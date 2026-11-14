"""Letter generation endpoints."""

from __future__ import annotations

from flask import Blueprint, abort, current_app, jsonify, request

from ..errors import ValidationError
from ..extensions import db
from ..letters.service import LetterInput, generate_letter
from ..llm import get_llm_client
from ..llm.catalog import is_known_model
from ..models import Campaign, GeneratedLetter, Offer, Profile
from ..serializers import letter_summary_to_dict, letter_to_dict
from ..validation import Validator, request_payload

MIN_DESCRIPTION_LENGTH = 40


def create_letters_blueprint() -> Blueprint:
    bp = Blueprint("letters", __name__)

    @bp.get("/letters")
    def list_letters():
        try:
            limit = int(request.args.get("limit", "20"))
        except ValueError:
            limit = 20
        limit = min(max(limit, 1), 100)

        letters = (
            GeneratedLetter.query.order_by(GeneratedLetter.created_at.desc())
            .limit(limit)
            .all()
        )
        return jsonify(
            {
                "letters": [letter_summary_to_dict(letter) for letter in letters],
                "total": GeneratedLetter.query.count(),
            }
        )

    @bp.get("/letters/<int:letter_id>")
    def get_letter(letter_id: int):
        letter = db.session.get(GeneratedLetter, letter_id)
        if letter is None:
            abort(404, description="Lettre introuvable.")
        return jsonify({"letter": letter_to_dict(letter)})

    @bp.post("/letters")
    def create_letter():
        data = Validator(request_payload())

        values = {
            "job_title": data.text("job_title", "Intitulé du poste", max_length=200, required=True),
            "company": data.text("company", "Entreprise", max_length=200, required=True),
            "source_url": data.text("source_url", "URL de l’offre", max_length=500),
            "job_description": data.text(
                "job_description", "Description de l’offre", max_length=30_000, required=True
            ),
            "instructions": data.text(
                "instructions", "Consigne supplémentaire", max_length=1_000
            ),
            "model": data.text("model", "Modèle", max_length=120),
            "offer_id": data.integer(
                "offer_id", "Offre", minimum=0, maximum=10**9, default=0
            ),
        }

        if values["job_description"] and len(values["job_description"]) < MIN_DESCRIPTION_LENGTH:
            data.add_error(
                "job_description",
                f"La description doit contenir au moins {MIN_DESCRIPTION_LENGTH} caractères.",
            )

        data.finish()

        profile = Profile.get_current()
        missing_fields: dict[str, str] = {}
        if not profile.cv_text.strip():
            missing_fields["cv_text"] = "Le CV est vide. Importe un PDF ou colle son texte dans le profil."
        if not profile.letter_template.strip():
            missing_fields["letter_template"] = "La lettre type est vide. Ajoute un modèle dans le profil."
        if missing_fields:
            raise ValidationError(
                "Complète ton profil avant de générer une lettre.", fields=missing_fields
            )

        settings = current_app.extensions["settings"]
        campaign = Campaign.get_current()
        model = values["model"] or campaign.letter_model or settings.letter_model

        offer_id = values["offer_id"] or None
        if offer_id:
            offer = db.session.get(Offer, offer_id)
            if offer is None or offer.deleted_at is not None:
                raise ValidationError(
                    "Offre introuvable.",
                    fields={"offer_id": "Cette offre n’existe plus."},
                )

        if not is_known_model(model):
            raise ValidationError(
                "Modèle inconnu.",
                fields={"model": f"Le modèle « {model} » n’est pas dans le catalogue."},
            )

        client = get_llm_client(settings)
        outcome = generate_letter(
            letter_input=LetterInput(
                job_title=values["job_title"],
                company=values["company"],
                job_description=values["job_description"],
                source_url=values["source_url"],
                instructions=values["instructions"],
                offer_id=offer_id,
            ),
            profile=profile,
            model=model,
            client=client,
            settings=settings,
        )

        letter = outcome.letter
        return (
            jsonify(
                {
                    "letter": letter_to_dict(letter),
                    "usage": {
                        "prompt_tokens": letter.prompt_tokens,
                        "completion_tokens": letter.completion_tokens,
                        "cost_usd": letter.cost_usd,
                        "duration_ms": letter.duration_ms,
                    },
                    "context_truncated": outcome.truncated_fields,
                }
            ),
            201,
        )

    @bp.put("/letters/<int:letter_id>")
    def update_letter(letter_id: int):
        letter = db.session.get(GeneratedLetter, letter_id)
        if letter is None:
            abort(404, description="Lettre introuvable.")

        data = Validator(request_payload())
        subject = data.text("subject", "Objet", max_length=300, required=True)
        body = data.text("body", "Lettre", max_length=30_000, required=True)
        data.finish()

        letter.subject = subject
        letter.body = body
        db.session.commit()

        return jsonify({"letter": letter_to_dict(letter)})

    @bp.delete("/letters/<int:letter_id>")
    def delete_letter(letter_id: int):
        letter = db.session.get(GeneratedLetter, letter_id)
        if letter is None:
            abort(404, description="Lettre introuvable.")

        db.session.delete(letter)
        db.session.commit()
        return jsonify({"deleted": True, "id": letter_id})

    return bp
