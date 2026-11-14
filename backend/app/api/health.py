"""Health check used by the Vue dashboard.

It reports what is wired up *without* leaking any secret. The frontend polls
this endpoint to display the connection state.
"""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify


def create_health_blueprint() -> Blueprint:
    bp = Blueprint("health", __name__)

    @bp.get("/health")
    def health():
        settings = current_app.extensions["settings"]

        return jsonify(
            {
                "status": "ok",
                "service": settings.app_name,
                "version": settings.version,
                "environment": "development" if settings.debug else "production",
                "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "llm": settings.public_llm_config,
                # Flipped to True as each phase lands. The dashboard reads this.
                "features": {
                    "database": False,
                    "profile": False,
                    "collectors": False,
                    "scoring": False,
                    "scheduler": False,
                },
            }
        )

    return bp
