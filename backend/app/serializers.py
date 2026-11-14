"""JSON serialization of database models.

Serializers are explicit rather than automatic: the API surface stays stable
even if the database schema evolves, and sensitive data (file paths) never
leaves the backend.
"""

from __future__ import annotations

from datetime import datetime

from .config import Settings
from .models import Campaign, GeneratedLetter, LLMCall, Profile


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def profile_to_dict(profile: Profile) -> dict[str, object]:
    return {
        "id": profile.id,
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "email": profile.email,
        "phone": profile.phone,
        "city": profile.city,
        "headline": profile.headline,
        "summary": profile.summary,
        "cv_filename": profile.cv_filename,
        "cv_text": profile.cv_text,
        "cv_uploaded_at": _iso(profile.cv_uploaded_at),
        "has_cv_file": bool(profile.cv_path),
        "letter_template": profile.letter_template,
        "created_at": _iso(profile.created_at),
        "updated_at": _iso(profile.updated_at),
    }


def campaign_to_dict(campaign: Campaign, settings: Settings) -> dict[str, object]:
    return {
        "id": campaign.id,
        "name": campaign.name,
        "keywords": list(campaign.keywords or []),
        "locations": list(campaign.locations or []),
        "contract_types": list(campaign.contract_types or []),
        "remote": campaign.remote,
        "radius_km": campaign.radius_km,
        "sources": list(campaign.sources or []),
        "starts_on": campaign.starts_on.isoformat() if campaign.starts_on else None,
        "ends_on": campaign.ends_on.isoformat() if campaign.ends_on else None,
        "frequency_hours": campaign.frequency_hours,
        "is_paused": campaign.is_paused,
        "status": campaign.status,
        "days_remaining": campaign.days_remaining,
        "score_threshold": campaign.score_threshold,
        "scoring_model": campaign.scoring_model or settings.scoring_model,
        "letter_model": campaign.letter_model or settings.letter_model,
        "last_scan_at": _iso(campaign.last_scan_at),
        "created_at": _iso(campaign.created_at),
        "updated_at": _iso(campaign.updated_at),
    }


def letter_summary_to_dict(letter: GeneratedLetter) -> dict[str, object]:
    """Lightweight payload for the history list (no full body)."""
    return {
        "id": letter.id,
        "job_title": letter.job_title,
        "company": letter.company,
        "subject": letter.subject,
        "source_url": letter.source_url,
        "model": letter.model,
        "prompt_tokens": letter.prompt_tokens,
        "completion_tokens": letter.completion_tokens,
        "cost_usd": letter.cost_usd,
        "duration_ms": letter.duration_ms,
        "created_at": _iso(letter.created_at),
        "updated_at": _iso(letter.updated_at),
    }


def letter_to_dict(letter: GeneratedLetter) -> dict[str, object]:
    payload = letter_summary_to_dict(letter)
    payload.update(
        {
            "body": letter.body,
            "job_description": letter.job_description,
            "instructions": letter.instructions,
            "prompt_version": letter.prompt_version,
        }
    )
    return payload


def llm_call_to_dict(call: LLMCall) -> dict[str, object]:
    return {
        "id": call.id,
        "task": call.task,
        "model": call.model,
        "prompt_version": call.prompt_version,
        "status": call.status,
        "prompt_tokens": call.prompt_tokens,
        "completion_tokens": call.completion_tokens,
        "cost_usd": call.cost_usd,
        "duration_ms": call.duration_ms,
        "error": call.error,
        "created_at": _iso(call.created_at),
    }
