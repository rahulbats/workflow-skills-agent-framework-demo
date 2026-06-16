"""Event Grid publishing helper for demo workflows.

Uses DefaultAzureCredential so local `az login` and managed identity both work.
If EVENT_GRID_TOPIC_ENDPOINT is not set, publishing is skipped.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from functools import lru_cache

from azure.eventgrid import EventGridEvent, EventGridPublisherClient

from .config import get_credential


@lru_cache(maxsize=1)
def _get_publisher() -> EventGridPublisherClient | None:
    endpoint = os.getenv("EVENT_GRID_TOPIC_ENDPOINT", "").strip()
    if not endpoint:
        return None
    return EventGridPublisherClient(endpoint=endpoint, credential=get_credential())


def publish_claim_decision_event(claim_id: str, decision_text: str) -> str:
    """Publish a claim decision event to Event Grid.

    Returns a status string instead of raising to keep demos resilient.
    """
    client = _get_publisher()
    if client is None:
        return "SKIPPED: EVENT_GRID_TOPIC_ENDPOINT not configured."

    subject_prefix = os.getenv("EVENT_GRID_SUBJECT_PREFIX", "claims/decision").strip("/")
    subject = f"/{subject_prefix}/{claim_id}"

    event = EventGridEvent(
        subject=subject,
        event_type="Contoso.Claims.DecisionGenerated",
        data_version="1.0",
        data={
            "claim_id": claim_id,
            "decision_text": decision_text,
            "published_utc": datetime.now(timezone.utc).isoformat(),
            "source": "demo1_orchestrator_workflow",
        },
    )

    try:
        client.send([event])
        return "OK: Published decision event to Event Grid."
    except Exception as ex:
        return f"ERROR: Event Grid publish failed: {ex}"
