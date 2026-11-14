from __future__ import annotations

from app import create_app
from app.config import Settings


def test_health_returns_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["service"] == "Job Finder API"
    assert body["version"] == "0.1.0"
    assert "time" in body
    assert body["features"]["database"] is True
    assert body["features"]["profile"] is True


def test_health_reports_llm_unconfigured_by_default(client):
    body = client.get("/api/health").get_json()

    assert body["llm"]["configured"] is False
    assert body["llm"]["scoring_model"]


def test_health_never_exposes_the_api_key():
    app = create_app(
        Settings(
            opencode_base_url="https://llm.example.test/v1",
            opencode_api_key="super-secret-key",
        )
    )
    response = app.test_client().get("/api/health")
    raw = response.get_data(as_text=True)

    assert response.get_json()["llm"]["configured"] is True
    assert "super-secret-key" not in raw
    assert "llm.example.test" not in raw


def test_api_index_lists_endpoints(client):
    body = client.get("/api").get_json()

    assert body["endpoints"]["health"] == "/api/health"


def test_unknown_route_returns_json_404(client):
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    body = response.get_json()
    assert body["error"]["code"] == 404
    assert body["error"]["name"] == "Not Found"
