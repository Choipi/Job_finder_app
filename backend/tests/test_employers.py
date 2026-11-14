from __future__ import annotations

from app.collectors.ats import ashby
from app.collectors.ats.base import CollectedOffer


def test_seed_watchlist_is_idempotent(client):
    first = client.post("/api/employers/seed").get_json()

    assert first["seed"]["total"] == 200
    assert first["seed"]["created"] == 200
    assert first["stats"]["total"] == 200
    assert first["stats"]["ready"] == 17

    second = client.post("/api/employers/seed").get_json()
    assert second["seed"]["created"] == 0
    assert second["seed"]["updated"] == 200
    assert second["stats"]["total"] == 200


def test_list_employers(client):
    client.post("/api/employers/seed")

    body = client.get("/api/employers?limit=500").get_json()

    assert len(body["employers"]) == 200
    assert body["stats"]["ready"] == 17
    assert body["stats"]["pending"] == 183
    assert body["employers"][0]["domain"]


def test_add_employer_detects_ats_from_careers_url(client):
    response = client.post(
        "/api/employers",
        json={
            "name": "Dust",
            "domain": "dust.tt",
            "careers_url": "https://jobs.ashbyhq.com/dust",
        },
    )

    assert response.status_code == 201
    employer = response.get_json()["employer"]
    assert employer["ats_type"] == "ashby"
    assert employer["ats_slug"] == "dust"
    assert employer["status"] == "ready"


def test_add_employer_rejects_invalid_domain(client):
    response = client.post("/api/employers", json={"domain": "not a domain"})

    assert response.status_code == 400
    assert "domain" in response.get_json()["error"]["fields"]


def test_toggle_employer(client):
    created = client.post(
        "/api/employers",
        json={"domain": "dust.tt", "careers_url": "https://jobs.ashbyhq.com/dust"},
    ).get_json()["employer"]

    response = client.patch(
        f"/api/employers/{created['id']}", json={"enabled": False}
    )

    assert response.status_code == 200
    assert response.get_json()["employer"]["enabled"] is False


def test_collect_employer_deduplicates(client, monkeypatch):
    created = client.post(
        "/api/employers",
        json={"domain": "dust.tt", "careers_url": "https://jobs.ashbyhq.com/dust"},
    ).get_json()["employer"]

    calls = {"count": 0}

    def fake_fetch(client, slug, *, limit=100):
        calls["count"] += 1
        return [
            CollectedOffer(
                external_id="1",
                title="Machine Learning Engineer",
                company="Dust",
                location="Paris",
                description="Build agents.",
                apply_url="https://jobs.ashbyhq.com/dust/1/application",
                source_url="https://jobs.ashbyhq.com/dust/1",
                remote="hybrid",
            ),
            CollectedOffer(
                external_id="2",
                title="Product Designer",
                company="Dust",
                location="Paris",
                description="Design agents.",
                apply_url="https://jobs.ashbyhq.com/dust/2/application",
                source_url="https://jobs.ashbyhq.com/dust/2",
            ),
        ]

    monkeypatch.setattr(ashby, "fetch", fake_fetch)

    first = client.post(f"/api/employers/{created['id']}/collect").get_json()
    assert first["collection"]["found"] == 2
    assert first["collection"]["new"] == 2
    assert first["employer"]["offer_count"] == 2

    second = client.post(f"/api/employers/{created['id']}/collect").get_json()
    assert second["collection"]["new"] == 0
    assert second["collection"]["updated"] == 2
    assert calls["count"] == 2

    offers = client.get("/api/offers").get_json()
    assert offers["total"] == 2
    assert offers["offers"][0]["apply_url"].startswith("https://jobs.ashbyhq.com/dust/")


def test_offer_detail_and_filters(client, monkeypatch):
    created = client.post(
        "/api/employers",
        json={"domain": "dust.tt", "careers_url": "https://jobs.ashbyhq.com/dust"},
    ).get_json()["employer"]

    monkeypatch.setattr(
        ashby,
        "fetch",
        lambda client, slug, *, limit=100: [
            CollectedOffer(
                external_id="1",
                title="AI Engineer",
                company="Dust",
                location="Paris",
                description="Long description",
                apply_url="https://jobs.ashbyhq.com/dust/1/application",
                source_url="https://jobs.ashbyhq.com/dust/1",
                remote="remote",
            )
        ],
    )
    client.post(f"/api/employers/{created['id']}/collect")

    listing = client.get("/api/offers?q=AI").get_json()
    assert listing["total"] == 1
    offer_id = listing["offers"][0]["id"]

    detail = client.get(f"/api/offers/{offer_id}").get_json()["offer"]
    assert detail["description"] == "Long description"
    assert detail["score_reasons"] == []
