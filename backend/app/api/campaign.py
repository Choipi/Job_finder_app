"""Campaign endpoints and the source catalogue."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from ..extensions import db
from ..llm.catalog import is_known_model
from ..models import Campaign
from ..serializers import campaign_to_dict
from ..sources import SOURCES, SOURCE_IDS
from ..validation import Validator, request_payload

CONTRACT_TYPES = ("CDI", "CDD", "Freelance", "Stage", "Alternance", "Intérim")
REMOTE_CHOICES = ("any", "onsite", "hybrid", "remote")
MAX_CAMPAIGN_DAYS = 365


def create_campaign_blueprint() -> Blueprint:
    bp = Blueprint("campaign", __name__)

    @bp.get("/sources")
    def list_sources():
        return jsonify({"sources": list(SOURCES)})

    @bp.get("/campaign")
    def get_campaign():
        settings = current_app.extensions["settings"]
        return jsonify({"campaign": campaign_to_dict(Campaign.get_current(), settings)})

    @bp.put("/campaign")
    def update_campaign():
        settings = current_app.extensions["settings"]
        data = Validator(request_payload())

        values = {
            "name": data.text("name", "Nom de la campagne", max_length=120, required=True),
            "keywords": data.string_list(
                "keywords", "Mots-clés", required=True, max_items=20, max_length=60
            ),
            "locations": data.string_list(
                "locations", "Lieux", max_items=15, max_length=80
            ),
            "contract_types": data.string_list(
                "contract_types",
                "Types de contrat",
                allowed=CONTRACT_TYPES,
                max_items=len(CONTRACT_TYPES),
            ),
            "remote": data.choice("remote", "Télétravail", REMOTE_CHOICES, default="any"),
            "radius_km": data.integer(
                "radius_km", "Rayon", minimum=0, maximum=200, default=30
            ),
            "sources": data.string_list(
                "sources",
                "Sources",
                allowed=SOURCE_IDS,
                max_items=len(SOURCE_IDS),
                required=False,
            ),
            "starts_on": data.date("starts_on", "Date de début"),
            "ends_on": data.date("ends_on", "Date de fin"),
            "frequency_hours": data.integer(
                "frequency_hours", "Fréquence de scan", minimum=1, maximum=168, default=6
            ),
            "score_threshold": data.integer(
                "score_threshold", "Seuil de pertinence", minimum=0, maximum=100, default=0
            ),
            "is_paused": data.boolean("is_paused", False),
            "scoring_model": data.text("scoring_model", "Modèle de scoring", max_length=120),
            "letter_model": data.text("letter_model", "Modèle de lettre", max_length=120),
        }

        starts_on = values["starts_on"]
        ends_on = values["ends_on"]
        if starts_on and ends_on:
            if ends_on < starts_on:
                data.add_error(
                    "ends_on", "La date de fin doit être postérieure à la date de début."
                )
            elif (ends_on - starts_on).days > MAX_CAMPAIGN_DAYS:
                data.add_error(
                    "ends_on", f"La campagne est limitée à {MAX_CAMPAIGN_DAYS} jours."
                )

        data.finish()

        campaign = Campaign.get_current()
        for key, value in values.items():
            if key == "scoring_model":
                value = value or settings.scoring_model
            elif key == "letter_model":
                value = value or settings.letter_model
            setattr(campaign, key, value)
        db.session.commit()

        return jsonify({"campaign": campaign_to_dict(campaign, settings)})

    @bp.put("/campaign/models")
    def update_campaign_models():
        data = Validator(request_payload())
        scoring_model = data.text("scoring_model", "Modèle de scoring", max_length=120, required=True)
        letter_model = data.text("letter_model", "Modèle de lettre", max_length=120, required=True)

        if scoring_model and not is_known_model(scoring_model):
            data.add_error("scoring_model", f"Le modèle « {scoring_model} » n’est pas dans le catalogue.")
        if letter_model and not is_known_model(letter_model):
            data.add_error("letter_model", f"Le modèle « {letter_model} » n’est pas dans le catalogue.")
        data.finish()

        campaign = Campaign.get_current()
        campaign.scoring_model = scoring_model
        campaign.letter_model = letter_model
        db.session.commit()

        settings = current_app.extensions["settings"]
        return jsonify({"campaign": campaign_to_dict(campaign, settings)})

    return bp
