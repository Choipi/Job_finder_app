"""Persist one row per LLM call.

This is the observability layer: tokens, estimated cost, latency and errors.
It is intentionally separate from the business tables so we can later compute
usage per task (letter, scoring, test) without parsing logs.
"""

from __future__ import annotations

from .client import LLMResult
from ..extensions import db
from ..models import LLMCall


def record_llm_call(
    *,
    task: str,
    model: str,
    prompt_version: str,
    status: str,
    duration_ms: int,
    result: LLMResult | None = None,
    error: str | None = None,
) -> LLMCall:
    call = LLMCall(
        task=task,
        model=model,
        prompt_version=prompt_version,
        status=status,
        prompt_tokens=result.prompt_tokens if result else 0,
        completion_tokens=result.completion_tokens if result else 0,
        cost_usd=result.cost_usd if result else 0.0,
        duration_ms=duration_ms,
        error=(error or "")[:1000],
    )
    db.session.add(call)
    return call
