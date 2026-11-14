"""Flask application factory.

Using a factory (instead of a global `app`) makes it possible to create one
application per test with a custom `Settings` instance.
"""

from __future__ import annotations

import logging

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from .api import register_blueprints
from .config import Settings


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or Settings()

    app = Flask(__name__)
    app.config.update(
        APP_NAME=settings.app_name,
        VERSION=settings.version,
        DEBUG=settings.debug,
        MAX_CONTENT_LENGTH=settings.max_upload_mb * 1024 * 1024,
        JSON_SORT_KEYS=False,
    )
    # Services read settings through `current_app.extensions["settings"]`.
    app.extensions["settings"] = settings

    CORS(app, resources={r"/api/*": {"origins": settings.cors_origins}})

    register_blueprints(app)
    _register_error_handlers(app)

    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    return app


def _register_error_handlers(app: Flask) -> None:
    """Return JSON for every API error, even when the client expects HTML."""

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return (
            jsonify(
                {
                    "error": {
                        "code": error.code,
                        "name": error.name,
                        "message": error.description,
                    }
                }
            ),
            error.code,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        # In development, let Flask show the real traceback instead of hiding
        # it behind a generic JSON response.
        if app.debug or app.testing:
            raise error

        app.logger.exception("Unhandled error: %s", error)
        return (
            jsonify(
                {
                    "error": {
                        "code": 500,
                        "name": "Internal Server Error",
                        "message": "An unexpected error occurred.",
                    }
                }
            ),
            500,
        )
