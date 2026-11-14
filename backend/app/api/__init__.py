"""API package: every HTTP route lives under the `/api` prefix.

Blueprints are built by functions instead of being module-level globals: a
Flask blueprint can only be registered once, and the app factory is called
several times in tests.
"""

from __future__ import annotations

from flask import Blueprint, Flask, current_app, jsonify

from .campaign import create_campaign_blueprint
from .employers import create_employers_blueprint
from .health import create_health_blueprint
from .letters import create_letters_blueprint
from .llm import create_llm_blueprint
from .profile import create_profile_blueprint


def create_api_blueprint() -> Blueprint:
    api = Blueprint("api", __name__, url_prefix="/api")

    @api.get("")
    @api.get("/")
    def index():
        """Small discovery endpoint, useful while learning the codebase."""
        settings = current_app.extensions["settings"]
        return jsonify(
            {
                "service": settings.app_name,
                "version": settings.version,
                "endpoints": {
                    "health": "/api/health",
                    "profile": "/api/profile",
                    "cv": "/api/profile/cv",
                    "campaign": "/api/campaign",
                    "campaign_models": "/api/campaign/models",
                    "sources": "/api/sources",
                    "letters": "/api/letters",
                    "models": "/api/models",
                    "llm_test": "/api/llm/test",
                    "llm_usage": "/api/llm/usage",
                    "employers": "/api/employers",
                    "employer_seed": "/api/employers/seed",
                    "employer_discover": "/api/employers/discover",
                    "employer_collect": "/api/employers/collect",
                    "offers": "/api/offers",
                },
            }
        )

    api.register_blueprint(create_health_blueprint())
    api.register_blueprint(create_profile_blueprint())
    api.register_blueprint(create_campaign_blueprint())
    api.register_blueprint(create_letters_blueprint())
    api.register_blueprint(create_llm_blueprint())
    api.register_blueprint(create_employers_blueprint())
    return api


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(create_api_blueprint())
