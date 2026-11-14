"""Employer watchlist service: seed, collect and normalize offers."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import func

from ..collectors.ats import get_adapter
from ..collectors.ats.base import AtsError, CollectedOffer
from ..extensions import db
from ..models import EmployerSource, Offer

SEED_PATH = Path(__file__).parent / "seed_ai_france.json"
MAX_DESCRIPTION_CHARS = 40_000


def seed_employers() -> dict[str, int]:
    """Load the AI France watchlist. Idempotent by domain.

    Existing user edits (enabled flag, ATS fields) are preserved; the seed
    only fills missing values.
    """
    entries = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    created = updated = 0

    for entry in entries:
        domain = str(entry.get("domain", "")).strip().lower()
        if not domain:
            continue

        employer = EmployerSource.query.filter_by(domain=domain).one_or_none()
        if employer is None:
            employer = EmployerSource(
                name=str(entry.get("name") or domain),
                domain=domain,
                sector=str(entry.get("sector") or "IA"),
                country=str(entry.get("country") or "FR"),
                city=str(entry.get("city") or ""),
                ats_type=str(entry.get("ats_type") or ""),
                ats_slug=str(entry.get("ats_slug") or ""),
                careers_url=str(entry.get("careers_url") or ""),
                origin=str(entry.get("origin") or "seed"),
                status=str(entry.get("status") or "pending"),
            )
            db.session.add(employer)
            created += 1
        else:
            updated += 1
            if not employer.ats_type and entry.get("ats_type"):
                employer.ats_type = str(entry["ats_type"])
                employer.ats_slug = str(entry.get("ats_slug") or "")
                employer.careers_url = str(entry.get("careers_url") or "")
                if employer.status in ("pending", "no_ats", "error"):
                    employer.status = "ready"

    db.session.commit()
    return {"created": created, "updated": updated, "total": len(entries)}


def collect_employer(
    employer: EmployerSource,
    *,
    client: httpx.Client,
    max_offers: int = 50,
) -> dict[str, int | str]:
    if not employer.ats_type or not employer.ats_slug:
        return {"found": 0, "new": 0, "updated": 0, "error": "ATS non détecté"}

    adapter = get_adapter(employer.ats_type)
    if adapter is None:
        return {
            "found": 0,
            "new": 0,
            "updated": 0,
            "error": f"ATS inconnu : {employer.ats_type}",
        }

    try:
        collected = adapter.fetch(client, employer.ats_slug, limit=max_offers)
    except (AtsError, httpx.HTTPError) as error:
        employer.status = "error"
        employer.last_error = str(error)[:500]
        employer.last_checked_at = datetime.now(timezone.utc)
        db.session.commit()
        return {"found": 0, "new": 0, "updated": 0, "error": str(error)}

    new_count = updated_count = 0
    now = datetime.now(timezone.utc)

    for item in collected:
        offer = _upsert_offer(employer, item, now)
        if offer is True:
            new_count += 1
        elif offer is False:
            updated_count += 1

    employer.status = "ready"
    employer.last_error = ""
    employer.last_checked_at = now
    employer.offer_count = Offer.query.filter_by(
        employer_id=employer.id, deleted_at=None
    ).count()
    db.session.commit()

    return {
        "found": len(collected),
        "new": new_count,
        "updated": updated_count,
        "error": "",
    }


def _upsert_offer(
    employer: EmployerSource, item: CollectedOffer, now: datetime
) -> bool | None:
    title = " ".join(item.title.split())
    if not title:
        return None

    company = " ".join((item.company or employer.name).split())
    location = " ".join(item.location.split())
    fingerprint = offer_fingerprint(title, company, location)
    description = item.description[:MAX_DESCRIPTION_CHARS]

    existing = Offer.query.filter_by(fingerprint=fingerprint).one_or_none()
    if existing is not None:
        existing.last_seen_at = now
        if description and len(description) > len(existing.description):
            existing.description = description
        if not existing.apply_url and item.apply_url:
            existing.apply_url = item.apply_url
        if not existing.source_url and item.source_url:
            existing.source_url = item.source_url
        if existing.published_at is None and item.published_at is not None:
            existing.published_at = item.published_at
        return False

    offer = Offer(
        employer_id=employer.id,
        source="employer_ats",
        external_id=item.external_id[:200],
        title=title[:300],
        company=company[:200],
        location=location[:200],
        remote=item.remote[:20],
        contract_type=item.contract_type[:80],
        salary=item.salary[:120],
        description=description,
        source_url=item.source_url[:700],
        apply_url=item.apply_url[:700],
        published_at=item.published_at,
        last_seen_at=now,
        fingerprint=fingerprint,
        status="new",
    )
    db.session.add(offer)
    return True


def collect_ready(limit: int = 5, max_offers: int = 50) -> dict[str, object]:
    employers = (
        EmployerSource.query.filter(
            EmployerSource.enabled.is_(True),
            EmployerSource.status == "ready",
            EmployerSource.ats_type != "",
        )
        .order_by(EmployerSource.last_checked_at.asc().nullsfirst())
        .limit(limit)
        .all()
    )

    results: list[dict[str, object]] = []
    totals = {"found": 0, "new": 0, "updated": 0, "errors": 0}
    client = httpx.Client(
        timeout=httpx.Timeout(25.0),
        follow_redirects=True,
        headers={
            "User-Agent": "JobFinder/0.1 (personal job search; local application)",
            "Accept": "application/json",
        },
    )
    try:
        for employer in employers:
            result = collect_employer(employer, client=client, max_offers=max_offers)
            totals["found"] += int(result["found"])
            totals["new"] += int(result["new"])
            totals["updated"] += int(result["updated"])
            if result["error"]:
                totals["errors"] += 1
            results.append(
                {
                    "id": employer.id,
                    "name": employer.name,
                    "ats": employer.ats_type,
                    **result,
                }
            )
            time.sleep(1.0)
    finally:
        client.close()

    return {
        "employers": len(employers),
        **totals,
        "results": results,
        "remaining": EmployerSource.query.filter(
            EmployerSource.enabled.is_(True),
            EmployerSource.status == "ready",
            EmployerSource.ats_type != "",
        ).count(),
    }


def employer_stats() -> dict[str, int]:
    total = EmployerSource.query.count()
    enabled = EmployerSource.query.filter_by(enabled=True).count()
    by_status = dict(
        db.session.query(EmployerSource.status, func.count(EmployerSource.id))
        .group_by(EmployerSource.status)
        .all()
    )
    offers = Offer.query.filter(Offer.deleted_at.is_(None)).count()

    return {
        "total": total,
        "enabled": enabled,
        "ready": int(by_status.get("ready", 0)),
        "pending": int(by_status.get("pending", 0)),
        "no_ats": int(by_status.get("no_ats", 0)),
        "errors": int(by_status.get("error", 0)),
        "offers": offers,
    }


def offer_fingerprint(title: str, company: str, location: str) -> str:
    normalized = "|".join(
        " ".join(value.lower().split()) for value in (title, company, location)
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
