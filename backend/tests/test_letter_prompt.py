from __future__ import annotations

from types import SimpleNamespace

from app.letters.service import LetterInput, build_messages, parse_letter


def letter_input() -> LetterInput:
    return LetterInput(
        job_title="Développeur Python",
        company="Acme",
        job_description="Construire une API Flask et des tests.",
    )


def profile(**overrides):
    base = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "headline": "Développeuse",
        "city": "Paris",
        "summary": "Résumé",
        "cv_text": "CV réel",
        "letter_template": "Madame, Monsieur,\n\nBien cordialement,",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_parse_letter_accepts_fenced_json():
    subject, body = parse_letter(
        '```json\n{"subject": "Objet", "body": "Corps"}\n```',
        fallback_subject="Fallback",
    )

    assert subject == "Objet"
    assert body == "Corps"


def test_parse_letter_accepts_json_surrounded_by_text():
    subject, body = parse_letter(
        'Voici la lettre :\n{"subject": "Objet", "body": "Corps"}\nBonne journée.',
        fallback_subject="Fallback",
    )

    assert subject == "Objet"
    assert body == "Corps"


def test_parse_letter_falls_back_to_raw_text():
    subject, body = parse_letter("Madame, Monsieur, voici ma lettre.", fallback_subject="Objet")

    assert subject == "Objet"
    assert body.startswith("Madame")


def test_build_messages_truncates_long_context():
    long_profile = profile(
        summary="s" * 4_000,
        cv_text="c" * 25_000,
        letter_template="t" * 9_000,
    )
    request = LetterInput(
        job_title="Développeur Python",
        company="Acme",
        job_description="d" * 20_000,
        instructions="i" * 2_000,
    )

    messages, truncated = build_messages(request, long_profile)

    assert set(truncated) == {"summary", "cv", "template", "description", "instructions"}
    assert messages[0].role == "system"
    assert messages[1].role == "user"
    assert "contenu tronqué" in messages[1].content
    assert "<entreprise>Acme</entreprise>" in messages[1].content
