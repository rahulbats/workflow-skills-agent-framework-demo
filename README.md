# Insurance Claims Agent Framework Demos

Two side-by-side demos of [Microsoft Agent Framework](https://learn.microsoft.com/agent-framework/overview/agent-framework-overview)
patterns for an **insurance-claims adjudication** scenario, backed by real
Azure OpenAI, Azure Cosmos DB, and Azure Blob Storage.

| Demo | Pattern | What it shows |
|---|---|---|
| **Demo 1** | Orchestrator **workflow** with **fan-out / fan-in** | Two specialist agents run in parallel — one queries Cosmos DB, one fetches the policy doc from Blob — and an orchestrator synthesizes the coverage decision. |
| **Demo 2** | **Single agent with two tools** | One `ClaimsAdjusterAgent` is given both lookups as tools and decides on its own when to call them and how to combine the results. |

Both demos read the same Cosmos record (`CLM-1001`) and the same policy
markdown (`POL-7788.md`) so you can compare the output and the wiring
side by side.

---

## Architecture

### Demo 1 — Workflow fan-out / fan-in

```
                        ┌──► ClaimDataAgent  ── tool ──► Cosmos DB
ClaimRequest ─► Dispatcher                                       ─┐
(claim_id)            └──► PolicyDocAgent  ── tool ──► Blob Stg ─┤
                                                                 ▼
                                              CoverageOrchestrator
                                          (final LLM synthesis call)
                                                                 │
                                                                 ▼
                                                       Coverage decision
```

### Demo 2 — Single agent with tools

```
                  ┌── tool: get_claim_from_cosmos ──► Cosmos DB
ClaimsAdjusterAgent
                  └── tool: get_policy_from_blob   ──► Blob Storage

(model picks the tool calls, then writes the coverage decision itself)
```

---

## Prerequisites

1. **Python 3.11+**
2. **Azure CLI** (`az`) and **Bicep CLI** (`az bicep install`).
3. An Azure subscription where you can create a new resource group plus
   Cosmos DB, Storage, and Azure OpenAI.

The Bicep template in [`infra/`](infra/) provisions everything for you
and assigns the data-plane RBAC your signed-in user needs:

- `Cognitive Services OpenAI User` on the AOAI account
- `Cosmos DB Built-in Data Contributor` on the Cosmos account
- `Storage Blob Data Contributor` on the storage account

---

## Setup

```powershell
# 1. Create / activate a venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Sign in to Azure (deploy.ps1 reads your signed-in identity for RBAC)
az login
az account set --subscription "<your-subscription>"

# 4. Provision the resource group + Cosmos + Blob + AOAI in one shot.
#    This also writes a ready-to-use .env at the repo root.
./infra/deploy.ps1 -Location eastus2 -ResourceGroupName rg-workflow-skills-agent-framework-demo

# 5. Seed Cosmos + Blob with the sample claim and policy doc
python -m shared.seed_data
```

> Prefer doing it by hand? You can still copy `.env.template` to `.env`,
> fill in endpoints from existing resources, and skip step 4.

---

## Run the demos

```powershell
# Demo 1 — orchestrator workflow
python -m demo1_orchestrator_workflow.main CLM-1001

# Demo 2 — single agent with tools
python -m demo2_single_agent_tools.main CLM-1001
```

You can also launch them from VS Code: open the **Run and Debug** panel
and pick **Demo 1 — Orchestrator Workflow** or **Demo 2 — Single Agent with Tools**.

---

## Project layout

```
workflow-skills-agent-framework-demo/
├── shared/
│   ├── config.py          # .env loading + Azure OpenAI chat-client factory
│   ├── data_clients.py    # Cosmos + Blob wrappers (DefaultAzureCredential)
│   ├── claim_tools.py     # @tool functions both demos consume
│   └── seed_data.py       # one-shot script to seed sample claim + policy
├── demo1_orchestrator_workflow/
│   └── main.py            # WorkflowBuilder fan-out → 2 agents → fan-in
├── demo2_single_agent_tools/
│   ├── main.py            # Single Agent with both tools
│   └── SKILL.md           # Externalized adjudicator instructions (loaded at runtime)
├── infra/
│   ├── main.bicep         # Subscription-scope: creates RG + invokes resources module
│   ├── resources.bicep    # Cosmos, Blob, AOAI + RBAC for your user
│   ├── main.bicepparam    # Parameters (region, RG name, model, capacity)
│   └── deploy.ps1         # One-shot: deploy + write .env
├── requirements.txt
├── .env.template
└── .vscode/launch.json    # Debug configs (incl. Foundry Agent Inspector)
```

---

## Talking points for the demo

- **Demo 1** showcases *deterministic* parallelism — the framework
  guarantees the two specialists run concurrently and the aggregator
  only fires after both finish (fan-in barrier). The wiring is visible
  and observable, which matters for regulated workflows like claims.
- **Demo 2** shows the *agentic* path — the model has agency to decide
  when to call each tool. With current models, it will typically issue
  both tool calls in parallel as well, so the latency is similar, but
  you give up the explicit graph and the easy mid-flight inspection.
- Demo 2's behavior lives in [`demo2_single_agent_tools/SKILL.md`](demo2_single_agent_tools/SKILL.md)
  — the operating procedure, output format, and hard rules are all in
  markdown. Edit the skill to retune the agent without touching code; a
  product manager or compliance reviewer can own that file.
- The same `shared/claim_tools.py` powers both demos, so you can
  emphasize that the **tools are the contract**: workflow vs. single
  agent is purely an orchestration choice on top.
