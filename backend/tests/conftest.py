from __future__ import annotations

import pytest

from app import create_app
from app.config import Settings


@pytest.fixture()
def app():
    application = create_app(Settings(debug=True))
    application.config.update(TESTING=True)
    return application


@pytest.fixture()
def client(app):
    return app.test_client()
