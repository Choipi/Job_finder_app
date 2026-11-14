from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.collectors.ats import ashby
from app.collectors.ats.base import CollectedOffer
from app.scans import campaign_scan_due
from app.scoring.service import parse_score, prefilter_reasons


def prepare_profile(client):
    client.put(
        "/api/profile",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "cv_text": "Python, Flask, SQLite, tests.",
            "letter_template": "Madame, Monsieur,\n\nBien cordialement,",
        },
    )


def create_offer(client, monkeypatch, *, title="AI Engineer", description="Build AI systems."):
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
                title=title,
                company="Dust",
                location="Paris",
                description=description,
                apply_url="https://jobs.ashbyhq.com/dust/1/application",
                source_url="https://jobs.ashbyhq.com/dust/1",
                remote="hybrid",
            )
        ],
    )
    client.post(f"/api/employers/{created['id']}/collect")
    return client.get("/api/offers").get_json()["offers"][0]


def set_campaign(client, **overrides):
    payload = {
        "name": "IA",
        "keywords": ["AI"],
        "locations": [],
        "contract_types": ["CDI"],
        "remote": "any",
        "radius_km": 30,
        "sources": [],
        "starts_on": "today",
        "ends_on": "tomorrow",
        "frequency_hours": 6,
        "score_threshold": 0,
        "is_paused": False,
        "scoring_model": "",
        "letter_model": "",
    }
    from datetime import date, timedelta

    today = date.today()
    payload["starts_on"] = today.isoformat()
    payload["ends_on"] = (today + timedelta(days=30)).isoformat()
    payload.update(overrides)
    response = client.put("/api/campaign", json=payload)
    assert response.status_code == 200, response.get_json()
    return response.get_json()["campaign"]


def test_score_offer_with_mock(client, monkeypatch):
    prepare_profile(client)
    offer = create_offer(client, monkeypatch, title="AI Engineer")

    response = client.post("/api/offers/score", json={"limit": 5})

    assert response.status_code == 200
    summary = response.get_json()["scoring"]
    assert summary["scored"] == 1

    detail = client.get(f"/api/offers/{offer['id']}").get_json()["offer"]
    assert detail["score"] == 72
    assert detail["score_status"] == "scored"
    assert detail["score_reasons"]
    assert detail["score_blockers"] == []


def test_prefilter_marks_offer_without_llm(client, monkeypatch):
    prepare_profile(client)
    create_offer(client, monkeypatch, title="Product Designer", description="Design interfaces.")
    set_campaign(client, keywords=["Python"])

    response = client.post("/api/offers/score", json={"limit": 5})

    assert response.status_code == 200
    summary = response.get_json()["scoring"]
    assert summary["filtered"] == 1
    assert summary["scored"] == 0

    offer = client.get("/api/offers").get_json()["offers"][0]
    assert offer["score"] == 0
    assert offer["score_status"] == "filtered"
    assert "mot-clé" in offer["score_reasons"][0].lower()


def test_offer_status_lifecycle(client, monkeypatch):
    offer = create_offer(client, monkeypatch)

    response = client.patch(f"/api/offers/{offer['id']}", json={"status": "applied"})

    assert response.status_code == 200
    assert response.get_json()["offer"]["status"] == "applied"

    invalid = client.patch(f"/api/offers/{offer['id']}", json={"status": "nope"})
    assert invalid.status_code == 400


def test_delete_restore_and_blacklist(client, monkeypatch):
    offer = create_offer(client, monkeypatch)

    deleted = client.delete(f"/api/offers/{offer['id']}")
    assert deleted.status_code == 200
    assert client.get("/api/offers").get_json()["total"] == 0
    assert client.get(f"/api/offers/{offer['id']}").status_code == 404

    # Re-collecting must not bring the deleted offer back.
    employer = client.get("/api/employers").get_json()["employers"][0]
    client.post(f"/api/employers/{employer['id']}/collect")
    assert client.get("/api/offers").get_json()["total"] == 0

    restored = client.post(f"/api/offers/{offer['id']}/restore")
    assert restored.status_code == 200
    assert client.get("/api/offers").get_json()["total"] == 1


def test_letter_linked_to_offer(client, monkeypatch):
    prepare_profile(client)
    offer = create_offer(client, monkeypatch)

    response = client.post(
        "/api/letters",
        json={
            "job_title": offer["title"],
            "company": offer["company"],
            "job_description": "Une offre de test suffisamment longue pour être acceptée.",
            "offer_id": offer["id"],
        },
    )

    assert response.status_code == 201
    assert response.get_json()["letter"]["offer_id"] == offer["id"]


def test_manual_scan(client, monkeypatch):
    import app.scans as scans

    monkeypatch.setattr(
        scans,
        "collect_ready",
        lambda **kwargs: {
            "employers": 2,
            "found": 10,
            "new": 4,
            "updated": 6,
            "errors": 0,
            "remaining": 3,
            "results": [],
        },
    )
    monkeypatch.setattr(
        scans,
        "score_offers",
        lambda limit: {
            "candidates": 4,
            "selected": 4,
            "scored": 3,
            "filtered": 1,
            "errors": 0,
            "remaining": 0,
        },
    )

    response = client.post("/api/scan", json={"collect_limit": 2, "score_limit": 4})

    assert response.status_code == 200
    body = response.get_json()
    assert body["scan"]["status"] == "ok"
    assert body["scan"]["employers_checked"] == 2
    assert body["scan"]["offers_new"] == 4
    assert body["scan"]["offers_scored"] == 3
    assert body["campaign"]["last_scan_at"] is not None
    assert client.get("/api/scans").get_json()["scans"][0]["id"] == body["scan"]["id"]


def test_campaign_scan_due():
    now = datetime.now(timezone.utc)
    campaign = SimpleNamespace(status="active", last_scan_at=None, frequency_hours=6)
    assert campaign_scan_due(campaign) is True

    campaign.last_scan_at = now
    assert campaign_scan_due(campaign) is False

    campaign.status = "paused"
    campaign.last_scan_at = None
    assert campaign_scan_due(campaign) is False


def test_parse_score():
    score, reasons, blockers = parse_score(
        '```json\n{"score": 88, "reasons": ["Bon match"], "blockers": []}\n```'
    )
    assert score == 88
    assert reasons == ["Bon match"]
    assert blockers == []


def test_prefilter_reasons():
    campaign = SimpleNamespace(
        keywords=["Python"],
        locations=["Paris"],
        remote="onsite",
    )
    offer = SimpleNamespace(
        title="Python Engineer",
        description="Flask",
        location="Paris",
        remote="onsite",
    )
    assert prefilter_reasons(offer, campaign) == []

    offer.location = "Lyon"
    reasons = prefilter_reasons(offer, campaign)
    assert any("Lieu" in reason for reason in reasons)
