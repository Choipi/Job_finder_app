from __future__ import annotations

from datetime import date, timedelta


def payload(**overrides):
    today = date.today()
    return {
        "name": "Recherche Python",
        "keywords": ["python", "flask"],
        "locations": ["Paris", "Remote"],
        "contract_types": ["CDI", "Freelance"],
        "remote": "hybrid",
        "radius_km": 40,
        "sources": ["france_travail", "adzuna"],
        "starts_on": today.isoformat(),
        "ends_on": (today + timedelta(days=30)).isoformat(),
        "frequency_hours": 12,
        "score_threshold": 60,
        "is_paused": False,
        "scoring_model": "",
        "letter_model": "",
        **overrides,
    }


def test_get_campaign_returns_defaults(client):
    response = client.get("/api/campaign")

    assert response.status_code == 200
    campaign = response.get_json()["campaign"]
    assert campaign["name"] == "Ma recherche"
    assert campaign["keywords"] == []
    assert campaign["status"] in {"active", "scheduled"}
    assert campaign["days_remaining"] is not None
    assert campaign["sources"] == []


def test_update_campaign_persists(client):
    response = client.put("/api/campaign", json=payload())

    assert response.status_code == 200
    campaign = response.get_json()["campaign"]
    assert campaign["keywords"] == ["python", "flask"]
    assert campaign["contract_types"] == ["CDI", "Freelance"]
    assert campaign["frequency_hours"] == 12
    assert campaign["status"] == "active"

    stored = client.get("/api/campaign").get_json()["campaign"]
    assert stored["name"] == "Recherche Python"
    assert stored["radius_km"] == 40


def test_campaign_model_falls_back_to_settings(client):
    campaign = client.put("/api/campaign", json=payload()).get_json()["campaign"]

    assert campaign["scoring_model"] == "deepseek-v4.1-flash"
    assert campaign["letter_model"] == "claude-haiku-5-5"


def test_campaign_rejects_end_before_start(client):
    response = client.put(
        "/api/campaign",
        json=payload(starts_on="2026-03-01", ends_on="2026-02-01"),
    )

    assert response.status_code == 400
    assert "ends_on" in response.get_json()["error"]["fields"]


def test_campaign_rejects_unknown_source(client):
    response = client.put("/api/campaign", json=payload(sources=["france_travail", "monster"]))

    assert response.status_code == 400
    assert "sources" in response.get_json()["error"]["fields"]


def test_campaign_requires_keywords(client):
    response = client.put("/api/campaign", json=payload(keywords=[]))

    assert response.status_code == 400
    assert "keywords" in response.get_json()["error"]["fields"]


def test_campaign_rejects_out_of_range_values(client):
    response = client.put(
        "/api/campaign", json=payload(frequency_hours=0, radius_km=999, score_threshold=101)
    )

    assert response.status_code == 400
    fields = response.get_json()["error"]["fields"]
    assert {"frequency_hours", "radius_km", "score_threshold"} <= set(fields)


def test_finished_campaign_status(client):
    campaign = client.put(
        "/api/campaign",
        json=payload(starts_on="2020-01-01", ends_on="2020-02-01"),
    ).get_json()["campaign"]

    assert campaign["status"] == "finished"
    assert campaign["days_remaining"] == 0


def test_sources_catalogue(client):
    response = client.get("/api/sources")

    assert response.status_code == 200
    sources = response.get_json()["sources"]
    ids = {source["id"] for source in sources}
    assert ids == {
        "france_travail",
        "adzuna",
        "wttj",
        "hellowork",
        "apec",
        "indeed",
        "linkedin",
    }
    assert all({"id", "label", "kind", "phase"} <= set(source) for source in sources)
