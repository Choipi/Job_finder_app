"""Flask application factory.

Using a factory (instead of a global `app`) makes it possible to create one
application per test with a custom `Settings` instance.
"""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from . import models  # noqa: F401 - imported so SQLAlchemy knows the tables
from .api import register_blueprints
from .cli import register_cli
from .config import Settings
from .errors import ValidationError
from .extensions import db
from .llm import LLMError
from .migrations import apply_sqlite_migrations
from .scheduler import start_scheduler


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or Settings()

    app = Flask(__name__)
    app.config.update(
        APP_NAME=settings.app_name,
        VERSION=settings.version,
        DEBUG=settings.debug,
        MAX_CONTENT_LENGTH=settings.max_upload_mb * 1024 * 1024,
        JSON_SORT_KEYS=False,
        SQLALCHEMY_DATABASE_URI=settings.database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        UPLOAD_DIR=str(settings.upload_dir),
    )
    # Services read settings through `current_app.extensions["settings"]`.
    app.extensions["settings"] = settings

    CORS(app, resources={r"/api/*": {"origins": settings.cors_origins}})

    _prepare_storage(settings)
    db.init_app(app)

    register_blueprints(app)
    register_cli(app)
    _register_error_handlers(app)

    with app.app_context():
        db.create_all()
        apply_sqlite_migrations()

    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    # httpx/httpcore are extremely verbose at DEBUG and would drown the
    # application logs. Keep warnings and errors only.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    start_scheduler(app)

    return app


def _prepare_storage(settings: Settings) -> None:
    """Create the folders SQLite and the CV uploads need, before first use."""
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    if settings.database_url.startswith("sqlite:///"):
        database_file = Path(settings.database_url.removeprefix("sqlite:///"))
        database_file.parent.mkdir(parents=True, exist_ok=True)


def _register_error_handlers(app: Flask) -> None:
    """Return JSON for every API error, even when the client expects HTML."""

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        return jsonify(error.to_dict()), 400

    @app.errorhandler(LLMError)
    def handle_llm_error(error: LLMError):
        return (
            jsonify(
                {
                    "error": {
                        "code": error.status_code,
                        "name": error.name,
                        "message": error.message,
                    }
                }
            ),
            error.status_code,
        )

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
