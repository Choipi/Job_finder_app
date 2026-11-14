from __future__ import annotations


def manual_payload(**overrides):
    return {
        "title": "Ingénieur Machine Learning",
        "company": "Acme",
        "location": "Paris",
        "source_url": "https://acme.example/jobs/1",
        "contract_type": "CDI",
        "remote": "hybrid",
        "description": "Nous cherchons un ingénieur ML pour construire des modèles et des APIs Python.",
        **overrides,
    }


def test_create_manual_offer(client):
    response = client.post("/api/offers", json=manual_payload())

    assert response.status_code == 201
    body = response.get_json()
    assert body["created"] is True
    offer = body["offer"]
    assert offer["source"] == "manual"
    assert offer["score"] is None
    assert offer["apply_url"] == "https://acme.example/jobs/1"
    assert client.get("/api/offers").get_json()["total"] == 1


def test_manual_offer_is_idempotent(client):
    client.post("/api/offers", json=manual_payload())

    response = client.post("/api/offers", json=manual_payload())

    assert response.status_code == 200
    assert response.get_json()["created"] is False
    assert client.get("/api/offers").get_json()["total"] == 1


def test_manual_offer_validates_description(client):
    response = client.post("/api/offers", json=manual_payload(description="court"))

    assert response.status_code == 400
    assert "description" in response.get_json()["error"]["fields"]


def test_manual_offer_restores_deleted_offer(client):
    created = client.post("/api/offers", json=manual_payload()).get_json()["offer"]
    client.delete(f"/api/offers/{created['id']}")
    assert client.get("/api/offers").get_json()["total"] == 0

    response = client.post("/api/offers", json=manual_payload())

    assert response.status_code == 200
    assert response.get_json()["created"] is False
    assert client.get("/api/offers").get_json()["total"] == 1
