"""Tools (function-calling targets) used by the claims agents.

Both demos import these. Demo 1 splits them across two specialist agents,
Demo 2 attaches both to a single agent so the model picks them itself.
"""

from __future__ import annotations

import json
from typing import Annotated

from pydantic import Field

from .data_clients import fetch_claim_record, fetch_policy_document
from .event_grid import publish_claim_decision_event


def get_claim_from_cosmos(
    claim_id: Annotated[
        str,
        Field(description="The claim identifier, e.g. 'CLM-1001'."),
    ],
) -> str:
    """Look up a structured claim record in Cosmos DB.

    Returns a JSON string with the full claim document, or an error message
    if the claim is not found.
    """
    record = fetch_claim_record(claim_id)
    if record is None:
        return json.dumps({"error": f"Claim '{claim_id}' not found in Cosmos DB."})
    # Strip Cosmos system properties before handing to the LLM
    cleaned = {k: v for k, v in record.items() if not k.startswith("_")}
    return json.dumps(cleaned, default=str)


def get_policy_from_blob(
    policy_id: Annotated[
        str,
        Field(description="The policy identifier, e.g. 'POL-7788'."),
    ],
) -> str:
    """Retrieve the full policy document (markdown) from Azure Blob Storage."""
    text = fetch_policy_document(policy_id)
    if text is None:
        return f"ERROR: Policy document '{policy_id}.md' not found in object store."
    return text


def publish_decision_to_event_grid(
    claim_id: Annotated[
        str,
        Field(description="The claim identifier, e.g. 'CLM-1001'."),
    ],
    decision_text: Annotated[
        str,
        Field(description="The final adjudication summary text to publish."),
    ],
) -> str:
    """Publish the final claim decision to Azure Event Grid."""
    return publish_claim_decision_event(claim_id=claim_id, decision_text=decision_text)
