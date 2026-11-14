from __future__ import annotations

import dataclasses

from app import create_app


def prepare_profile(client):
    response = client.put(
        "/api/profile",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
            "headline": "Développeuse Python",
            "summary": "Cinq ans de back-end Python.",
            "cv_text": "Experiences : Flask, SQLite, tests automatises.",
            "letter_template": "Madame, Monsieur,\n\nJe vous adresse ma candidature.\n\nBien cordialement,\nAda Lovelace",
        },
    )
    assert response.status_code == 200
    return response.get_json()["profile"]


def letter_payload(**overrides):
    return {
        "job_title": "Développeur Python",
        "company": "Acme",
        "source_url": "https://acme.example/jobs/1",
        "job_description": "Nous cherchons un développeur Python pour construire une API Flask et des tests.",
        "instructions": "",
        **overrides,
    }


def test_generate_letter_with_mock(client):
    prepare_profile(client)

    response = client.post("/api/letters", json=letter_payload())

    assert response.status_code == 201
    body = response.get_json()
    letter = body["letter"]
    assert letter["job_title"] == "Développeur Python"
    assert letter["company"] == "Acme"
    assert "Mode démo" in letter["body"]
    assert letter["prompt_version"] == "letter/v1"
    assert letter["model"] == "claude-haiku-5-5"
    assert body["usage"]["prompt_tokens"] > 0
    assert body["context_truncated"] == []


def test_letter_history_and_detail(client):
    prepare_profile(client)
    created = client.post("/api/letters", json=letter_payload()).get_json()["letter"]

    listing = client.get("/api/letters").get_json()
    assert listing["total"] == 1
    assert listing["letters"][0]["subject"] == created["subject"]
    assert "body" not in listing["letters"][0]

    detail = client.get(f"/api/letters/{created['id']}").get_json()["letter"]
    assert detail["body"] == created["body"]
    assert detail["job_description"].startswith("Nous cherchons")


def test_update_and_delete_letter(client):
    prepare_profile(client)
    letter = client.post("/api/letters", json=letter_payload()).get_json()["letter"]

    updated = client.put(
        f"/api/letters/{letter['id']}",
        json={"subject": "Objet corrigé", "body": "Corps corrigé."},
    )
    assert updated.status_code == 200
    assert updated.get_json()["letter"]["subject"] == "Objet corrigé"

    deleted = client.delete(f"/api/letters/{letter['id']}")
    assert deleted.status_code == 200
    assert client.get(f"/api/letters/{letter['id']}").status_code == 404


def test_letter_requires_profile_content(client):
    response = client.post("/api/letters", json=letter_payload())

    assert response.status_code == 400
    fields = response.get_json()["error"]["fields"]
    assert "cv_text" in fields
    assert "letter_template" in fields


def test_letter_requires_description(client):
    prepare_profile(client)

    response = client.post("/api/letters", json=letter_payload(job_description="trop court"))

    assert response.status_code == 400
    assert "job_description" in response.get_json()["error"]["fields"]


def test_letter_rejects_unknown_model(client):
    prepare_profile(client)

    response = client.post("/api/letters", json=letter_payload(model="gpt-42"))

    assert response.status_code == 400
    assert "model" in response.get_json()["error"]["fields"]


def test_letter_without_key_returns_503(app, client):
    prepare_profile(client)
    settings = app.extensions["settings"]
    real_settings = dataclasses.replace(
        settings, llm_provider="opencode_go", opencode_api_key=""
    )
    real_app = create_app(real_settings)
    real_app.config.update(TESTING=True)

    response = real_app.test_client().post("/api/letters", json=letter_payload())

    assert response.status_code == 503
    body = response.get_json()
    assert body["error"]["name"] == "LLM Not Configured"
    assert "OPENCODE_API_KEY" in body["error"]["message"]


def test_letter_accepts_explicit_catalog_model(client):
    prepare_profile(client)

    response = client.post(
        "/api/letters", json=letter_payload(model="deepseek-v4.1-flash")
    )

    assert response.status_code == 201
    assert response.get_json()["letter"]["model"] == "deepseek-v4.1-flash"
