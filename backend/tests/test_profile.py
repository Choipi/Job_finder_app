from __future__ import annotations

from io import BytesIO

from fpdf import FPDF


def make_pdf(*lines: str) -> bytes:
    """Build a tiny text-based PDF, the kind a real CV would be."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    for line in lines or ("Developpeur Python", "5 ans d experience"):
        pdf.cell(0, 8, line)
        pdf.ln(8)
    return bytes(pdf.output())


def test_get_profile_returns_defaults(client):
    response = client.get("/api/profile")

    assert response.status_code == 200
    profile = response.get_json()["profile"]
    assert profile["first_name"] == ""
    assert profile["cv_text"] == ""
    assert profile["has_cv_file"] is False
    assert profile["cv_uploaded_at"] is None


def test_update_profile_persists(client):
    payload = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "phone": "06 12 34 56 78",
        "city": "Paris",
        "headline": "Développeuse Python",
        "summary": "J’aime les systèmes simples et testés.",
        "cv_text": "Experiences...",
        "letter_template": "Madame, Monsieur,\n\nJe vous écris...",
    }

    response = client.put("/api/profile", json=payload)

    assert response.status_code == 200
    stored = client.get("/api/profile").get_json()["profile"]
    assert stored["first_name"] == "Ada"
    assert stored["email"] == "ada@example.com"
    assert stored["headline"] == "Développeuse Python"
    assert stored["letter_template"].startswith("Madame")


def test_update_profile_rejects_invalid_email(client):
    response = client.put("/api/profile", json={"email": "not-an-email"})

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["code"] == 400
    assert "email" in body["error"]["fields"]


def test_upload_cv_extracts_text(client):
    response = client.post(
        "/api/profile/cv",
        data={"file": (BytesIO(make_pdf("Developpeur Python", "Flask et SQLite")), "cv.pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    profile = response.get_json()["profile"]
    assert profile["has_cv_file"] is True
    assert profile["cv_filename"] == "cv.pdf"
    assert "Developpeur Python" in profile["cv_text"]
    assert "Flask et SQLite" in profile["cv_text"]
    assert profile["cv_uploaded_at"] is not None


def test_upload_cv_rejects_non_pdf(client):
    response = client.post(
        "/api/profile/cv",
        data={"file": (BytesIO(b"just text"), "cv.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "file" in response.get_json()["error"]["fields"]


def test_upload_cv_rejects_fake_pdf(client):
    response = client.post(
        "/api/profile/cv",
        data={"file": (BytesIO(b"not a pdf"), "cv.pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "file" in response.get_json()["error"]["fields"]


def test_upload_cv_rejects_pdf_without_text(client):
    # A truly empty PDF (no page content) cannot be parsed into text.
    blank = FPDF()
    blank.add_page()

    response = client.post(
        "/api/profile/cv",
        data={"file": (BytesIO(bytes(blank.output())), "blank.pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "file" in response.get_json()["error"]["fields"]


def test_delete_cv_clears_text(client):
    client.post(
        "/api/profile/cv",
        data={"file": (BytesIO(make_pdf("Developpeur Python")), "cv.pdf")},
        content_type="multipart/form-data",
    )

    response = client.delete("/api/profile/cv")

    assert response.status_code == 200
    profile = response.get_json()["profile"]
    assert profile["has_cv_file"] is False
    assert profile["cv_text"] == ""
    assert profile["cv_filename"] == ""
