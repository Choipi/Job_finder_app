"""LLM scoring of offers."""

from __future__ import annotations

from ..config import Settings
from ..llm import LLMClient, LLMError, LLMMessage
from ..llm.catalog import is_known_model
from ..llm.telemetry import record_llm_call
from ..models import Campaign, Offer, OfferScore, Profile
from ..extensions import db

PROMPT_VERSION = "score/v1"
TASK = "scoring"
MAX_OUTPUT_TOKENS = 900
LIMITS = {
    "summary": 3_000,
    "cv": 8_000,
    "description": 12_000,
}
