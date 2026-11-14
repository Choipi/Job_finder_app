"""In-process scheduler for automatic scans.

APScheduler runs a tick every minute. The tick only launches a scan when the
campaign is active and its frequency is due, so the duration configured in the
campaign is respected.

The scheduler is optional (`SCHEDULER_ENABLED=true`) because a scan can call a
paid LLM. It is also disabled in tests.
"""

from __future__ import annotations

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

from .config import Settings
from .extensions import db
from .models import Campaign
from .scans import campaign_scan_due, run_scan

logger = logging.getLogger(__name__)


def start_scheduler(app: Flask) -> BackgroundScheduler | None:
    settings: Settings = app.extensions["settings"]
    if not settings.scheduler_enabled:
        return None

    # The Werkzeug reloader starts the app twice; only the child should schedule.
    if settings.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return None

    scheduler = BackgroundScheduler(daemon=True)

    def tick() -> None:
        with app.app_context():
            campaign = Campaign.get_current()
            if not campaign_scan_due(campaign):
                return
            logger.info("Scheduled scan starting (campaign=%s)", campaign.name)
            try:
                run = run_scan(
                    trigger="scheduler",
                    collect_limit=settings.scan_collect_employers,
                    score_limit=settings.scan_score_offers,
                )
                logger.info(
                    "Scheduled scan finished status=%s new=%s scored=%s errors=%s",
                    run.status,
                    run.offers_new,
                    run.offers_scored,
                    run.errors,
                )
            except Exception:  # noqa: BLE001 - keep the scheduler alive
                logger.exception("Scheduled scan crashed")
                db.session.rollback()

    scheduler.add_job(
        tick,
        trigger="interval",
        seconds=settings.scheduler_interval_seconds,
        id="scan-tick",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    app.extensions["scheduler"] = scheduler
    logger.info(
        "Scheduler started (tick=%ss, collect=%s, score=%s)",
        settings.scheduler_interval_seconds,
        settings.scan_collect_employers,
        settings.scan_score_offers,
    )
    return scheduler
