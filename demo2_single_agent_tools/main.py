"""Demo 2 — A single agent with SkillsProvider.

Same business outcome as Demo 1, but using SkillsProvider from agent-framework
to manage the skills in a structured, discoverable way. The agent's behavior 
is defined declaratively in `SKILL.md` (loaded at runtime). Edit that file to 
tune the persona, output format, or hard rules without touching code.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_framework import Agent, Skill, SkillsProvider, skill

from shared.claim_tools import get_claim_from_cosmos, get_policy_from_blob
from shared.config import get_chat_client


SKILL_PATH = Path(__file__).parent / "SKILL.md"


def load_skill_instructions(path: Path = SKILL_PATH) -> str:
    """Read SKILL.md and return the instructions."""
    return path.read_text(encoding="utf-8").strip()


@skill
class ClaimsSkill:
    """Claims processing skill with two resources."""

    @skill.resource
    async def claim_lookup(self, claim_id: str) -> dict:
        """Look up claim details from Cosmos DB."""
        return await get_claim_from_cosmos(claim_id)

    @skill.resource
    async def policy_lookup(self, policy_id: str) -> dict:
        """Look up policy details from Blob Storage."""
        return await get_policy_from_blob(policy_id)


def build_agent() -> Agent:
    claims_skill = ClaimsSkill()
    skills_provider = SkillsProvider(skills=[claims_skill])

    return Agent(
        client=get_chat_client(),
        name="ClaimsAdjusterAgent",
        instructions=load_skill_instructions(),
        skills_provider=skills_provider,
    )


async def main(claim_id: str = "CLM-1001") -> None:
    agent = build_agent()

    print(f"\n=== Demo 2: Single agent with tools — adjudicating {claim_id} ===\n")

    prompt = f"Please adjudicate claim {claim_id} and produce the coverage decision."

    response = await agent.run(prompt)

    print("=== Final coverage decision ===\n")
    print(response.text)


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "CLM-1001"
    asyncio.run(main(target))
