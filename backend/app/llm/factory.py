"""Choose the LLM client from configuration.

Business code calls this factory and never knows which provider is behind it.
"""

from __future__ import annotations

from ..config import Settings
from .client import LLMClient
from .errors import LLMNotConfigured
from .mock import MockLLMClient
from .opencode_go import OpenCodeGoClient


def get_llm_client(settings: Settings) -> LLMClient:
    provider = settings.llm_provider

    if provider == "mock":
        return MockLLMClient()

    if provider == "opencode_go":
        if not settings.llm_configured:
            raise LLMNotConfigured(
                "OPENCODE_API_KEY est absent. Renseigne-le dans .env puis redémarre Flask, "
                "ou passe LLM_PROVIDER=mock pour développer sans clé."
            )
        return OpenCodeGoClient(
            base_url=settings.opencode_base_url,
            api_key=settings.opencode_api_key,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
            session_id=settings.llm_session_id,
        )

    raise LLMNotConfigured(
        f"Fournisseur LLM inconnu : « {provider} ». Valeurs acceptées : opencode_go, mock."
    )
