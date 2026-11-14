from __future__ import annotations

import pytest

from app import create_app
from app.config import Settings


@pytest.fixture()
def app(tmp_path):
    settings = Settings(
        debug=True,
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        upload_dir=tmp_path / "uploads",
        # Tests never hit the network: the deterministic mock is the default.
        llm_provider="mock",
        # Explicit empties keep tests independent from the developer's .env.
        opencode_base_url="",
        opencode_api_key="",
    )
    application = create_app(settings)
    application.config.update(TESTING=True)
    return application


@pytest.fixture()
def client(app):
    return app.test_client()
