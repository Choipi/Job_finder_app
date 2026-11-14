from __future__ import annotations


def test_models_catalogue(client):
    response = client.get("/api/models")

    assert response.status_code == 200
    body = response.get_json()
    assert body["provider"] == "mock"
    assert body["mock"] is True
    assert body["defaults"]["letter"] == "claude-haiku-5-5"
    assert len(body["models"]) >= 10

    model = body["models"][0]
    assert {"id", "label", "pricing", "tags", "free"} <= set(model)
    assert "input_per_million" in model["pricing"]


def test_connection_test_uses_mock(client):
    response = client.post("/api/llm/test", json={"model": "deepseek-v4.1-flash"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["ok"] is True
    assert "mode démo" in body["reply"].lower()
    assert body["usage"]["prompt_tokens"] > 0


def test_usage_endpoint_aggregates_calls(client):
    client.post("/api/llm/test", json={})

    body = client.get("/api/llm/usage").get_json()

    assert body["totals"]["calls"] >= 1
    assert body["totals"]["total_tokens"] > 0
    assert body["recent"][0]["task"] == "test"
    assert body["recent"][0]["status"] == "ok"


def test_usage_is_empty_initially(client):
    body = client.get("/api/llm/usage").get_json()

    assert body["totals"]["calls"] == 0
    assert body["totals"]["cost_usd"] == 0
    assert body["recent"] == []


def test_update_campaign_models(client):
    response = client.put(
        "/api/campaign/models",
        json={"scoring_model": "deepseek-v4.1-flash", "letter_model": "gpt-6-luna"},
    )

    assert response.status_code == 200
    campaign = response.get_json()["campaign"]
    assert campaign["scoring_model"] == "deepseek-v4.1-flash"
    assert campaign["letter_model"] == "gpt-6-luna"

    stored = client.get("/api/campaign").get_json()["campaign"]
    assert stored["letter_model"] == "gpt-6-luna"


def test_update_campaign_models_rejects_unknown(client):
    response = client.put(
        "/api/campaign/models",
        json={"scoring_model": "unknown-model", "letter_model": "gpt-6-luna"},
    )

    assert response.status_code == 400
    assert "scoring_model" in response.get_json()["error"]["fields"]
