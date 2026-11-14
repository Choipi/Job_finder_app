"""Profile endpoints: identity, CV and reference cover letter."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from ..errors import ValidationError
from ..extensions import db
from ..models import Profile, utcnow
from ..serializers import profile_to_dict
from ..services.cv import CvError, store_cv
from ..validation import Validator, request_payload


def create_profile_blueprint() -> Blueprint:
    bp = Blueprint("profile", __name__)

    @bp.get("/profile")
    def get_profile():
        return jsonify({"profile": profile_to_dict(Profile.get_current())})

    @bp.put("/profile")
    def update_profile():
        data = Validator(request_payload())

        # Read everything first: the model is only touched once the whole
        # payload is valid.
        values = {
            "first_name": data.text("first_name", "Prénom", max_length=80),
            "last_name": data.text("last_name", "Nom", max_length=80),
            "email": data.email("email", "Email"),
            "phone": data.text("phone", "Téléphone", max_length=40),
            "city": data.text("city", "Ville", max_length=120),
            "headline": data.text("headline", "Poste visé", max_length=160),
            "summary": data.text("summary", "Présentation", max_length=5000),
            "cv_text": data.text("cv_text", "Texte du CV", max_length=40_000),
            "letter_template": data.text(
                "letter_template", "Lettre type", max_length=20_000
            ),
        }
        data.finish()

        profile = Profile.get_current()
        for key, value in values.items():
            setattr(profile, key, value)
        db.session.commit()

        return jsonify({"profile": profile_to_dict(profile)})

    @bp.post("/profile/cv")
    def upload_cv():
        if "file" not in request.files:
            raise ValidationError(
                "Aucun fichier reçu.", fields={"file": "Choisis un fichier PDF."}
            )

        settings = current_app.extensions["settings"]
        try:
            stored = store_cv(request.files["file"], settings.upload_dir)
        except CvError as error:
            raise ValidationError(str(error), fields={"file": str(error)}) from error

        profile = Profile.get_current()

        # Remove the previous file only once the new one is safely stored.
        if profile.cv_path:
            previous = Path(profile.cv_path)
            if previous != stored.path:
                previous.unlink(missing_ok=True)

        profile.cv_path = str(stored.path)
        profile.cv_filename = stored.original_name
        profile.cv_text = stored.text
        profile.cv_uploaded_at = utcnow()
        db.session.commit()

        return jsonify({"profile": profile_to_dict(profile)})

    @bp.delete("/profile/cv")
    def delete_cv():
        profile = Profile.get_current()

        if profile.cv_path:
            Path(profile.cv_path).unlink(missing_ok=True)

        profile.cv_path = ""
        profile.cv_filename = ""
        profile.cv_text = ""
        profile.cv_uploaded_at = None
        db.session.commit()

        return jsonify({"profile": profile_to_dict(profile)})

    return bp
