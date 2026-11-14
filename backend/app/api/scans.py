"""Manual scan and scheduler status endpoints."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from ..models import Campaign, ScanRun
from ..scans import run_scan
from ..serializers import campaign_to_dict, scan_to_dict
from ..validation import Validator, request_payload


def create_scans_blueprint() -> Blueprint:
    bp = Blueprint("scans", __name__)

    @bp.post("/scan")
    def scan_now():
        data = Validator(request_payload())
        collect_limit = data.integer(
            "collect_limit", "Employeurs à collecter", minimum=0, maximum=25, default=3
        )
        max_offers = data.integer(
            "max_offers", "Offres par employeur", minimum=1, maximum=200, default=50
        )
        score_limit = data.integer(
            "score_limit", "Offres à scorer", minimum=0, maximum=50, default=10
        )
        data.finish()

        run = run_scan(
            trigger="manual",
            collect_limit=collect_limit,
            max_offers=max_offers,
            score_limit=score_limit,
        )
        settings = current_app.extensions["settings"]
        campaign = Campaign.get_current()

        return jsonify(
            {
                "scan": scan_to_dict(run),
                "campaign": campaign_to_dict(campaign, settings),
            }
        )

    @bp.get("/scans")
    def list_scans():
        limit = 20
        try:
            limit = min(max(int(request.args.get("limit", "20")), 1), 100)
        except ValueError:
            pass
        runs = (
            ScanRun.query.order_by(ScanRun.started_at.desc()).limit(limit).all()
        )
        return jsonify({"scans": [scan_to_dict(run) for run in runs]})

    @bp.get("/scheduler")
    def scheduler_status():
        settings = current_app.extensions["settings"]
        scheduler = current_app.extensions.get("scheduler")
        next_run = None
        if scheduler is not None:
            job = scheduler.get_job("scan-tick")
            if job and job.next_run_time:
                next_run = job.next_run_time.isoformat()

        return jsonify(
            {
                "enabled": settings.scheduler_enabled,
                "running": scheduler is not None,
                "next_run_at": next_run,
                "interval_seconds": settings.scheduler_interval_seconds,
            }
        )

    return bp
