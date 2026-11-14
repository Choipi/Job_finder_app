"""Scoring pipeline: deterministic pre-filter, then LLM judgement.

The pre-filter is deliberately cheap and explainable. It removes offers that
are obviously outside the campaign (keywords, location, remote), and only the
remaining offers are sent to the model. A filtered offer still receives a
score record, so the UI can explain why it was not evaluated.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from flask import current_app

from ..config import Settings
from ..extensions import db
from ..llm import LLMClient, LLMError, LLMMessage, get_llm_client
from ..llm.catalog import is_known_model
from ..llm.telemetry import record_llm_call
from ..models import Campaign, Offer, OfferScore, Profile
from ..models import utcnow

PROMPT_VERSION = "score/v1"
TASK = "scoring"
MAX_OUTPUT_TOKENS = 2_000
PROMPT_PATH = Path(__file__).parent / "prompts" / "score_system.md"

LIMITS = {
    "summary": 3_000,
    "cv": 8_000,
    "description": 12_000,
}


@dataclass(frozen=True)
class ScoreOutcome:
    offer_id: int
    status: str
    score: int | None
    reason: str = ""
    error: str = ""


def prefilter_reasons(offer: Offer, campaign: Campaign) -> list[str]:
    reasons: list[str] = []
    text = f"{offer.title}\n{offer.description}".lower()

    if campaign.keywords:
        if not any(str(keyword).lower() in text for keyword in campaign.keywords):
            reasons.append("Aucun mot-clé de la campagne dans l’offre.")

    if campaign.locations:
        location = offer.location.lower()
        location_match = any(str(place).lower() in location for place in campaign.locations)
        remote_match = campaign.remote == "remote" and offer.remote == "remote"
        if not location_match and not remote_match:
            reasons.append(f"Lieu hors zone : {offer.location or 'non précisé'}.")

    if campaign.remote != "any" and offer.remote != campaign.remote:
        reasons.append(
            f"Mode de travail incompatible : {offer.remote or 'non précisé'} "
            f"(campagne : {campaign.remote})."
        )

    return reasons


def score_offers(limit: int = 20) -> dict[str, int]:
    settings: Settings = current_app.extensions["settings"]
    campaign = Campaign.get_current()
    profile = Profile.get_current()

    if not profile.summary.strip() and not profile.cv_text.strip():
        return {
            "candidates": 0,
            "selected": 0,
            "scored": 0,
            "filtered": 0,
            "errors": 0,
            "remaining": 0,
            "skipped": "profile_empty",
        }

    model = campaign.scoring_model or settings.scoring_model
    if not is_known_model(model):
        model = settings.scoring_model

    candidates = (
        Offer.query.filter(Offer.deleted_at.is_(None))
        .order_by(Offer.published_at.desc(), Offer.id.desc())
        .limit(max(limit * 10, 200))
        .all()
    )
    todo = [offer for offer in candidates if _needs_scoring(offer, model)][:limit]

    # Raises LLMNotConfigured before touching offers if the key is missing.
    client = get_llm_client(settings)

    counts = {
        "candidates": len(candidates),
        "selected": len(todo),
        "scored": 0,
        "filtered": 0,
        "errors": 0,
        "remaining": max(len(candidates) - len(todo), 0),
        "skipped": "",
    }

    for offer in todo:
        reasons = prefilter_reasons(offer, campaign)
        if reasons:
            _save_score(
                offer,
                status="filtered",
                score=0,
                reasons=reasons,
                blockers=[],
                model=model,
            )
            counts["filtered"] += 1
            db.session.commit()
            continue

        try:
            messages = build_score_messages(offer, profile, campaign)
            result = client.complete(
                messages,
                model=model,
                temperature=0.0,
                max_tokens=MAX_OUTPUT_TOKENS,
                json_mode=True,
            )
            score, reasons, blockers = parse_score(result.content)
            _save_score(
                offer,
                status="scored",
                score=score,
                reasons=reasons,
                blockers=blockers,
                model=model,
            )
            record_llm_call(
                task=TASK,
                model=result.model,
                prompt_version=PROMPT_VERSION,
                status="ok",
                duration_ms=result.duration_ms,
                result=result,
            )
            counts["scored"] += 1
        except (LLMError, ValueError) as error:
            message = str(error)
            _save_score(
                offer,
                status="error",
                score=None,
                reasons=[],
                blockers=[],
                model=model,
                error=message,
            )
            record_llm_call(
                task=TASK,
                model=model,
                prompt_version=PROMPT_VERSION,
                status="error",
                duration_ms=0,
                error=message,
            )
            counts["errors"] += 1
        db.session.commit()

    return counts


def build_score_messages(
    offer: Offer, profile: Profile, campaign: Campaign
) -> list[LLMMessage]:
    summary = _truncate(profile.summary, LIMITS["summary"])
    cv = _truncate(profile.cv_text, LIMITS["cv"])
    description = _truncate(offer.description, LIMITS["description"])

    user_message = "\n".join(
        [
            "<profil>",
            f"{profile.first_name} {profile.last_name}".strip() or "Non renseigné",
            profile.headline,
            summary,
            "</profil>",
            "",
            "<criteres>",
            f"mots-clés: {', '.join(campaign.keywords or []) or 'aucun'}",
            f"lieux: {', '.join(campaign.locations or []) or 'aucun'}",
            f"télétravail: {campaign.remote}",
            f"contrats: {', '.join(campaign.contract_types or []) or 'aucun'}",
            "</criteres>",
            "",
            "<cv>",
            cv or "Non renseigné",
            "</cv>",
            "",
            "<offre>",
            f"<titre>{offer.title}</titre>",
            f"<entreprise>{offer.company}</entreprise>",
            f"<lieu>{offer.location or 'non précisé'}</lieu>",
            f"<remote>{offer.remote or 'non précisé'}</remote>",
            f"<contrat>{offer.contract_type or 'non précisé'}</contrat>",
            "<description>",
            description,
            "</description>",
            "</offre>",
            "",
            "Évalue la pertinence de cette offre pour ce candidat.",
        ]
    )

    return [
        LLMMessage(role="system", content=PROMPT_PATH.read_text(encoding="utf-8")),
        LLMMessage(role="user", content=user_message),
    ]


def parse_score(raw: str) -> tuple[int, list[str], list[str]]:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    candidates = [text]
    first, last = text.find("{"), text.rfind("}")
    if first != -1 and last > first:
        candidates.append(text[first : last + 1])

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        try:
            score = int(data.get("score"))
        except (TypeError, ValueError):
            continue
        score = min(max(score, 0), 100)
        reasons = _string_list(data.get("reasons"))
        blockers = _string_list(data.get("blockers"))
        return score, reasons, blockers

    raise ValueError("Le modèle n’a pas renvoyé un score JSON exploitable.")


def _save_score(
    offer: Offer,
    *,
    status: str,
    score: int | None,
    reasons: list[str],
    blockers: list[str],
    model: str,
    error: str = "",
) -> None:
    record = offer.score_record
    if record is None:
        record = OfferScore(offer=offer)
        db.session.add(record)

    record.status = status
    record.score = score
    record.reasons = reasons[:5]
    record.blockers = blockers[:5]
    record.model = model
    record.prompt_version = PROMPT_VERSION
    record.error = error[:500]
    record.updated_at = utcnow()

    offer.score = score
    offer.score_reasons = reasons[:5]


def _needs_scoring(offer: Offer, model: str) -> bool:
    record = offer.score_record
    if record is None:
        return True
    if record.status == "error":
        return True
    return record.prompt_version != PROMPT_VERSION or record.model != model


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n[…contenu tronqué…]"


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append(item.strip()[:300])
    return result[:5]


__all__ = [
    "PROMPT_VERSION",
    "build_score_messages",
    "parse_score",
    "prefilter_reasons",
    "score_offers",
]
