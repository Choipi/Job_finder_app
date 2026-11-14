"""One collection + scoring pass, manual or scheduled."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .employers.service import collect_ready
from .extensions import db
from .models import Campaign, ScanRun, utcnow
from .scoring.service import score_offers


def run_scan(
    *,
    trigger: str = "manual",
    collect_limit: int = 5,
    max_offers: int = 50,
    score_limit: int = 20,
) -> ScanRun:
    run = ScanRun(trigger=trigger, status="running")
    db.session.add(run)
    db.session.commit()

    campaign = Campaign.get_current()
    errors = 0
    detail: dict[str, object] = {}

    try:
        if collect_limit > 0:
            collection = collect_ready(limit=collect_limit, max_offers=max_offers)
            run.employers_checked = int(collection["employers"])
            run.offers_found = int(collection["found"])
            run.offers_new = int(collection["new"])
            errors += int(collection["errors"])
            detail["collection"] = collection
    except Exception as error:  # noqa: BLE001 - a scan must leave an audit trace
        errors += 1
        detail["collection_error"] = str(error)[:1000]

    try:
        if score_limit > 0:
            scoring = score_offers(limit=score_limit)
            run.offers_scored = int(scoring["scored"])
            errors += int(scoring["errors"])
            detail["scoring"] = scoring
    except Exception as error:  # noqa: BLE001 - e.g. LLM key missing
        errors += 1
        detail["scoring_error"] = str(error)[:1000]

    run.errors = errors
    run.status = "ok" if errors == 0 else ("partial" if run.offers_found or run.offers_scored else "error")
    run.finished_at = utcnow()
    run.detail = detail
    campaign.last_scan_at = utcnow()
    db.session.commit()

    return run


def campaign_scan_due(campaign: Campaign) -> bool:
    if campaign.status != "active":
        return False
    if campaign.last_scan_at is None:
        return True
    last = campaign.last_scan_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last >= timedelta(hours=campaign.frequency_hours)
