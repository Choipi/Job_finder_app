"""LLM observability and configuration endpoints.

- GET  /api/models      : catalogue used by the model pickers
- POST /api/llm/test    : one tiny call to verify key, endpoint and model
- GET  /api/llm/usage   : aggregated tokens/cost + recent calls
"""

from __future__ import annotations

import time

from flask import Blueprint, current_app, jsonify
from sqlalchemy import func

from ..errors import ValidationError
from ..extensions import db
from ..llm import LLMError, LLMMessage, get_llm_client
from ..llm.catalog import MODELS, is_known_model, public_catalog
from ..llm.telemetry import record_llm_call
from ..models import Campaign, LLMCall
from ..serializers import llm_call_to_dict
from ..validation import Validator, request_payload

TEST_PROMPT_VERSION = "connection/v1"
TEST_TASK = "test"


def create_llm_blueprint() -> Blueprint:
    bp = Blueprint("llm", __name__)

    @bp.get("/models")
    def list_models():
        settings = current_app.extensions["settings"]
        return jsonify(
            {
                "models": public_catalog(),
                "defaults": {
                    "scoring": settings.scoring_model,
                    "letter": settings.letter_model,
                },
                "provider": settings.llm_provider,
                "mock": settings.llm_provider == "mock",
            }
        )

    @bp.post("/llm/test")
    def test_llm():
        settings = current_app.extensions["settings"]
        data = Validator(request_payload())
        campaign = Campaign.get_current()
        model = data.text("model", "Modèle", max_length=120) or campaign.letter_model or settings.letter_model
        if not is_known_model(model):
            data.add_error("model", f"Le modèle « {model} » n’est pas dans le catalogue.")
        data.finish()

        client = get_llm_client(settings)
        started = time.perf_counter()

        try:
            result = client.complete(
                [
                    LLMMessage(
                        role="system",
                        content="Tu es un test de connexion. Réponds uniquement par OK.",
                    ),
                    LLMMessage(role="user", content="Réponds uniquement par OK."),
                ],
                model=model,
                max_tokens=64,
            )
        except LLMError as error:
            record_llm_call(
                task=TEST_TASK,
                model=model,
                prompt_version=TEST_PROMPT_VERSION,
                status="error",
                duration_ms=int((time.perf_counter() - started) * 1000),
                error=error.message,
            )
            db.session.commit()
            raise

        record_llm_call(
            task=TEST_TASK,
            model=model,
            prompt_version=TEST_PROMPT_VERSION,
            status="ok",
            duration_ms=result.duration_ms,
            result=result,
        )
        db.session.commit()

        return jsonify(
            {
                "ok": True,
                "model": result.model,
                "reply": result.content.strip()[:200],
                "duration_ms": result.duration_ms,
                "usage": {
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "cost_usd": result.cost_usd,
                },
            }
        )

    @bp.get("/llm/usage")
    def usage():
        count, prompt_tokens, completion_tokens, cost = db.session.query(
            func.count(LLMCall.id),
            func.coalesce(func.sum(LLMCall.prompt_tokens), 0),
            func.coalesce(func.sum(LLMCall.completion_tokens), 0),
            func.coalesce(func.sum(LLMCall.cost_usd), 0.0),
        ).one()

        recent = LLMCall.query.order_by(LLMCall.created_at.desc()).limit(20).all()

        return jsonify(
            {
                "totals": {
                    "calls": int(count),
                    "prompt_tokens": int(prompt_tokens),
                    "completion_tokens": int(completion_tokens),
                    "total_tokens": int(prompt_tokens) + int(completion_tokens),
                    "cost_usd": round(float(cost), 6),
                },
                "recent": [llm_call_to_dict(call) for call in recent],
                "models": len(MODELS),
            }
        )

    return bp
