"""JSON serialization of database models.

Serializers are explicit rather than automatic: the API surface stays stable
even if the database schema evolves, and sensitive data (file paths) never
leaves the backend.
"""

from __future__ import annotations

from datetime import datetime

from .config import Settings
from .models import Campaign, EmployerSource, GeneratedLetter, LLMCall, Offer, Profile, ScanRun


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
        "offer_id": letter.offer_id,
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


def employer_to_dict(employer: EmployerSource) -> dict[str, object]:
    return {
        "id": employer.id,
        "name": employer.name,
        "domain": employer.domain,
        "sector": employer.sector,
        "country": employer.country,
        "city": employer.city,
        "ats_type": employer.ats_type,
        "ats_slug": employer.ats_slug,
        "careers_url": employer.careers_url,
        "enabled": employer.enabled,
        "origin": employer.origin,
        "status": employer.status,
        "last_checked_at": _iso(employer.last_checked_at),
        "last_error": employer.last_error,
        "offer_count": employer.offer_count,
        "created_at": _iso(employer.created_at),
        "updated_at": _iso(employer.updated_at),
    }


def offer_summary_to_dict(offer: Offer) -> dict[str, object]:
    score = offer.score_record
    return {
        "id": offer.id,
        "employer_id": offer.employer_id,
        "source": offer.source,
        "title": offer.title,
        "company": offer.company,
        "location": offer.location,
        "remote": offer.remote,
        "contract_type": offer.contract_type,
        "salary": offer.salary,
        "apply_url": offer.apply_url,
        "published_at": _iso(offer.published_at),
        "score": offer.score,
        "score_status": score.status if score else None,
        "score_reasons": list(score.reasons or []) if score else list(offer.score_reasons or []),
        "score_blockers": list(score.blockers or []) if score else [],
        "scored_at": _iso(score.updated_at) if score else None,
        "status": offer.status,
        "created_at": _iso(offer.created_at),
    }


def offer_to_dict(offer: Offer) -> dict[str, object]:
    payload = offer_summary_to_dict(offer)
    payload.update(
        {
            "description": offer.description,
            "source_url": offer.source_url,
            "external_id": offer.external_id,
            "score_reasons": list(offer.score_record.reasons or [])
            if offer.score_record
            else list(offer.score_reasons or []),
            "last_seen_at": _iso(offer.last_seen_at),
            "updated_at": _iso(offer.updated_at),
        }
    )
    return payload


def scan_to_dict(run: ScanRun) -> dict[str, object]:
    return {
        "id": run.id,
        "trigger": run.trigger,
        "status": run.status,
        "started_at": _iso(run.started_at),
        "finished_at": _iso(run.finished_at),
        "employers_checked": run.employers_checked,
        "offers_found": run.offers_found,
        "offers_new": run.offers_new,
        "offers_scored": run.offers_scored,
        "errors": run.errors,
        "detail": run.detail or {},
    }
