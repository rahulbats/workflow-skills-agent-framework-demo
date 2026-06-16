"""Demo 1 — Orchestrator workflow that fans out to two specialist agents.

Topology
========

    Dispatcher (custom Executor)
         │ fan-out (broadcasts the claim_id)
         ├──────► ClaimDataAgent  (tool: get_claim_from_cosmos)
         └──────► PolicyDocAgent  (tool: get_policy_from_blob)
                          │ fan-in (collects both responses)
                          ▼
                  CoverageOrchestrator (custom Executor)
                  - calls the chat client one final time to
                    synthesise a coverage decision and yields it
                    as the workflow output

The two specialist agents run **in parallel**; their tool calls (Cosmos /
Blob) happen concurrently.  The aggregator only fires once both responses
have arrived (fan-in barrier).
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_framework import (
    Agent,
    AgentExecutor,
    AgentExecutorRequest,
    AgentExecutorResponse,
    Executor,
    Message,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)
from typing_extensions import Never

from shared.claim_tools import (
    get_claim_from_cosmos,
    get_policy_from_blob,
    publish_decision_to_event_grid,
)
from shared.config import get_chat_client


# ---------------------------------------------------------------------------
# Workflow input / executors
# ---------------------------------------------------------------------------

@dataclass
class ClaimRequest:
    """Top-level message that enters the workflow."""

    claim_id: str


CLAIM_AGENT_INSTRUCTIONS = """\
You are the ClaimDataAgent. You retrieve the structured claim record for the
given claim_id from Cosmos DB using the `get_claim_from_cosmos` tool, then
return a concise bulleted summary of the key fields (claimant, policy_id,
date_of_loss, loss_type, claim_amount, description, status). Always include
the `policy_id` exactly as stored. Do not make up information.
"""

POLICY_AGENT_INSTRUCTIONS = """\
You are the PolicyDocAgent. You retrieve the policy document for the given
policy_id from object storage using the `get_policy_from_blob` tool, then
return a concise bulleted summary of: coverage limits, deductibles, notable
exclusions, and any fast-track / pre-approval rules. Do not make up
information.

If the user message contains a claim_id but no policy_id, first ask for the
policy_id by responding with the literal string `NEEDS_POLICY_ID` — but in
this workflow the dispatcher always provides both, so you should normally
proceed straight to the tool call.
"""


class ClaimDispatcher(Executor):
    """Fan-out source: turns the inbound ClaimRequest into one
    AgentExecutorRequest per specialist agent.

    Both downstream AgentExecutors receive the same prompt — they each
    decide how to act on it via their own instructions/tools.
    """

    @handler
    async def dispatch(
        self,
        request: ClaimRequest,
        ctx: WorkflowContext[AgentExecutorRequest],
    ) -> None:
        # We need the policy_id up front so the policy agent can do its lookup
        # in parallel with the claim agent. Fetch it once here.
        from shared.data_clients import fetch_claim_record

        claim = fetch_claim_record(request.claim_id)
        if claim is None:
            await ctx.yield_output(
                f"ERROR: claim '{request.claim_id}' not found in Cosmos DB."
            )
            return
        policy_id = claim["policy_id"]

        prompt = (
            f"Please look up and summarise the data for claim {request.claim_id} "
            f"under policy {policy_id}."
        )
        message = Message(role="user", contents=[prompt])
        agent_request = AgentExecutorRequest(
            messages=[message],
            should_respond=True,
        )
        # ctx.send_message broadcasts to all fan-out targets
        await ctx.send_message(agent_request)


class CoverageOrchestrator(Executor):
    """Fan-in sink: receives both AgentExecutorResponses and asks the LLM
    one final time to synthesise a coverage decision."""

    def __init__(self, id: str = "coverage_orchestrator") -> None:
        super().__init__(id=id)
        self._chat_client = get_chat_client()

    @handler
    async def synthesize(
        self,
        responses: list[AgentExecutorResponse],
        ctx: WorkflowContext[Never, str],
    ) -> None:
        # Pull the last assistant text from each specialist
        sections: list[str] = []
        for r in responses:
            agent_name = r.executor_id
            text = r.agent_response.text or "(no content)"
            sections.append(f"### {agent_name}\n{text}")

        synthesis_prompt = (
            "You are the orchestrator for an insurance-claim adjudicator.\n"
            "Two specialist agents have just reported their findings below. "
            "Combine them into a single, clear coverage decision for a human "
            "claims adjuster. Include:\n"
            "  1. A one-line recommendation (Approve fast-track / Approve / "
            "Refer to senior adjuster / Deny).\n"
            "  2. The numeric figures the adjuster needs (claim amount, "
            "applicable deductible, expected payout).\n"
            "  3. A short justification grounded ONLY in the two reports.\n"
            "  4. Any open questions or missing data.\n\n"
            + "\n\n".join(sections)
        )
        result = await self._chat_client.get_response(
            messages=[Message(role="user", contents=[synthesis_prompt])]
        )
        await ctx.yield_output(result.text)


# ---------------------------------------------------------------------------
# Workflow assembly
# ---------------------------------------------------------------------------

def build_workflow():
    chat_client = get_chat_client()

    claim_agent = AgentExecutor(
        Agent(
            client=chat_client,
            name="ClaimDataAgent",
            instructions=CLAIM_AGENT_INSTRUCTIONS,
            tools=[get_claim_from_cosmos],
        ),
        id="ClaimDataAgent",
    )
    policy_agent = AgentExecutor(
        Agent(
            client=chat_client,
            name="PolicyDocAgent",
            instructions=POLICY_AGENT_INSTRUCTIONS,
            tools=[get_policy_from_blob],
        ),
        id="PolicyDocAgent",
    )

    dispatcher = ClaimDispatcher(id="dispatcher")
    aggregator = CoverageOrchestrator()

    return (
        WorkflowBuilder(start_executor=dispatcher)
        .add_fan_out_edges(dispatcher, [claim_agent, policy_agent])
        .add_fan_in_edges([claim_agent, policy_agent], aggregator)
        .build()
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main(claim_id: str = "CLM-1001") -> None:
    workflow = build_workflow()

    print(f"\n=== Demo 1: Orchestrator workflow — adjudicating {claim_id} ===\n")

    final_output: str | None = None
    async for event in workflow.run(ClaimRequest(claim_id=claim_id), stream=True):
        # Surface workflow lifecycle so the demo visibly "shows the work"
        if event.type == "executor_invoked":
            print(f"[invoked]   {event.executor_id}")
        elif event.type == "executor_completed":
            print(f"[completed] {event.executor_id}")
        elif event.type == "output" and event.executor_id == "coverage_orchestrator":
            final_output = str(event.data)

    print("\n=== Final coverage decision ===\n")
    print(final_output or "(no output produced)")

    if final_output:
        publish_status = publish_decision_to_event_grid(
            claim_id=claim_id,
            decision_text=final_output,
        )
        print(f"\n[EventGrid] {publish_status}")


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "CLM-1001"
    asyncio.run(main(target))
