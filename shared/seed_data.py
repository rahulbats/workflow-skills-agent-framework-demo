"""One-shot script that seeds Cosmos DB and Blob Storage with sample data.

Run once before the demos:

    python -m shared.seed_data

Creates the database / container / blob container if they do not exist,
then upserts a sample claim and uploads a sample policy markdown file.
"""

from __future__ import annotations

import json
import os

from azure.cosmos import CosmosClient, PartitionKey
from azure.storage.blob import BlobServiceClient

from .config import (
    BLOB_ACCOUNT_URL,
    BLOB_CONTAINER,
    COSMOS_CONTAINER,
    COSMOS_DATABASE,
    COSMOS_ENDPOINT,
    get_credential,
)

SAMPLE_CLAIM = {
    "id": "CLM-1001",
    "claim_id": "CLM-1001",
    "policy_id": "POL-7788",
    "claimant_name": "Jordan Rivera",
    "date_of_loss": "2026-05-18",
    "loss_type": "Auto collision",
    "incident_location": "Seattle, WA",
    "claim_amount_usd": 8450.00,
    "description": (
        "Insured was rear-ended at a stoplight on Aurora Ave N. Bumper, trunk lid, "
        "and rear quarter panel sustained damage. No injuries reported. Police "
        "report #SPD-2026-44219 filed at the scene."
    ),
    "adjuster_notes": "Photos uploaded; awaiting body shop estimate.",
    "status": "open",
}

SAMPLE_POLICY_ID = "POL-7788"
SAMPLE_POLICY_MD = """\
# Auto Insurance Policy POL-7788

**Policyholder:** Jordan Rivera
**Effective:** 2026-01-01 to 2026-12-31
**Vehicle:** 2022 Toyota Camry SE

## Coverage Summary

| Coverage              | Limit (USD) | Deductible (USD) |
|-----------------------|-------------|-------------------|
| Bodily Injury (per person) | 100,000     | -                 |
| Bodily Injury (per accident) | 300,000   | -                 |
| Property Damage       | 50,000      | -                 |
| Collision             | Actual cash value | 1,000        |
| Comprehensive         | Actual cash value | 500          |
| Rental Reimbursement  | 30/day, 900 max | -              |

## Notable Exclusions

- Damage from racing or off-road use
- Intentional acts by the insured
- Mechanical breakdown unrelated to a covered incident
- Damage while the vehicle is being used for ridesharing

## Claims Notes

Collision claims under USD 10,000 with a filed police report and no bodily
injury are generally eligible for fast-track adjudication subject to the
USD 1,000 collision deductible.
"""


def seed_cosmos() -> None:
    print(f"[cosmos] connecting to {COSMOS_ENDPOINT}")
    cosmos_key = os.getenv("COSMOS_KEY", "").strip()
    disable_ssl = os.getenv("COSMOS_EMULATOR_DISABLE_SSL_VERIFY", "false").lower() in {
        "1",
        "true",
        "yes",
    }
    if cosmos_key:
        kwargs: dict[str, object] = {
            "url": COSMOS_ENDPOINT,
            "credential": cosmos_key,
        }
        if disable_ssl:
            kwargs["connection_verify"] = False
        client = CosmosClient(**kwargs)
    else:
        client = CosmosClient(COSMOS_ENDPOINT, credential=get_credential())
    db = client.create_database_if_not_exists(id=COSMOS_DATABASE)
    container = db.create_container_if_not_exists(
        id=COSMOS_CONTAINER,
        partition_key=PartitionKey(path="/claim_id"),
    )
    container.upsert_item(SAMPLE_CLAIM)
    print(f"[cosmos] upserted claim {SAMPLE_CLAIM['claim_id']}")
    print(json.dumps(SAMPLE_CLAIM, indent=2))


def seed_blob() -> None:
    print(f"[blob] connecting to {BLOB_ACCOUNT_URL}")
    service = BlobServiceClient(account_url=BLOB_ACCOUNT_URL, credential=get_credential())
    container = service.get_container_client(BLOB_CONTAINER)
    if not container.exists():
        container.create_container()
        print(f"[blob] created container '{BLOB_CONTAINER}'")
    blob_name = f"{SAMPLE_POLICY_ID}.md"
    container.upload_blob(name=blob_name, data=SAMPLE_POLICY_MD, overwrite=True)
    print(f"[blob] uploaded {blob_name} ({len(SAMPLE_POLICY_MD)} bytes)")


def main() -> None:
    seed_cosmos()
    seed_blob()
    print("\nDone. Run the demos:")
    print("  python -m demo1_orchestrator_workflow.main")
    print("  python -m demo2_single_agent_tools.main")


if __name__ == "__main__":
    main()
