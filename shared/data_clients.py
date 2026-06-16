"""Thin Cosmos DB + Blob Storage wrappers used by the agent tools.

Both clients use Microsoft Entra auth via `DefaultAzureCredential`. Make sure
the signed-in identity has:
  * Cosmos DB Built-in Data Reader (or Contributor) on the account
  * Storage Blob Data Reader on the storage account
"""

from __future__ import annotations

import os
from functools import lru_cache

from azure.cosmos import ContainerProxy, CosmosClient
from azure.storage.blob import BlobServiceClient, ContainerClient

from .config import (
    BLOB_ACCOUNT_URL,
    BLOB_CONTAINER,
    COSMOS_CONTAINER,
    COSMOS_DATABASE,
    COSMOS_ENDPOINT,
    get_credential,
)


# ---------------------------------------------------------------- Cosmos
def _build_cosmos_client() -> CosmosClient:
    """Create a Cosmos client for cloud (AAD) or local emulator (key)."""
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
        return CosmosClient(**kwargs)

    return CosmosClient(COSMOS_ENDPOINT, credential=get_credential())


@lru_cache(maxsize=1)
def _cosmos_container() -> ContainerProxy:
    client = _build_cosmos_client()
    db = client.get_database_client(COSMOS_DATABASE)
    return db.get_container_client(COSMOS_CONTAINER)


def fetch_claim_record(claim_id: str) -> dict | None:
    """Read a single claim document from Cosmos by id.

    Assumes the container's partition key is `/claim_id`.
    """
    container = _cosmos_container()
    try:
        return container.read_item(item=claim_id, partition_key=claim_id)
    except Exception:  # noqa: BLE001 — surface absence as None to the agent
        return None


# ------------------------------------------------------------------ Blob
@lru_cache(maxsize=1)
def _blob_container() -> ContainerClient:
    service = BlobServiceClient(account_url=BLOB_ACCOUNT_URL, credential=get_credential())
    return service.get_container_client(BLOB_CONTAINER)


def fetch_policy_document(policy_id: str) -> str | None:
    """Download a policy document (text/markdown) from Blob Storage.

    Blob name convention: ``{policy_id}.md``.
    """
    blob = _blob_container().get_blob_client(f"{policy_id}.md")
    if not blob.exists():
        return None
    stream = blob.download_blob()
    return stream.readall().decode("utf-8")
