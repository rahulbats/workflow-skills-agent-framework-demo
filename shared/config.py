"""Configuration + Azure OpenAI chat client factory.

Loads `.env` and exposes a single `get_chat_client()` helper that both demos
reuse so the AOAI wiring lives in one place.
"""

from __future__ import annotations

import os
from functools import lru_cache

from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load .env once on import. override=False so values already in the environment
# (e.g. set by Azure / a launch.json envFile) take precedence.
load_dotenv(override=False)


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable '{name}'. "
            "Copy .env.template to .env and fill in the values."
        )
    return value


# Cosmos -----------------------------------------------------------------
COSMOS_ENDPOINT = _require("COSMOS_ENDPOINT")
COSMOS_DATABASE = _require("COSMOS_DATABASE")
COSMOS_CONTAINER = _require("COSMOS_CONTAINER")

# Blob -------------------------------------------------------------------
BLOB_ACCOUNT_URL = _require("BLOB_ACCOUNT_URL")
BLOB_CONTAINER = _require("BLOB_CONTAINER")

# Azure OpenAI -----------------------------------------------------------
AZURE_OPENAI_ENDPOINT = _require("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_CHAT_MODEL = _require("AZURE_OPENAI_CHAT_MODEL")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")  # optional


@lru_cache(maxsize=1)
def get_credential() -> DefaultAzureCredential:
    """Return a cached Azure credential.

    DefaultAzureCredential picks up `az login`, managed identity, env-vars, etc.
    For local dev, run `az login` once.
    """
    return DefaultAzureCredential()


def get_chat_client() -> OpenAIChatClient:
    """Build the Azure OpenAI chat client used by all agents in both demos."""
    kwargs: dict[str, object] = {
        "model": AZURE_OPENAI_CHAT_MODEL,
        "azure_endpoint": AZURE_OPENAI_ENDPOINT,
        "credential": get_credential(),
    }
    if AZURE_OPENAI_API_VERSION:
        kwargs["api_version"] = AZURE_OPENAI_API_VERSION
    return OpenAIChatClient(**kwargs)  # type: ignore[arg-type]
