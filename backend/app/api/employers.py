"""Employer watchlist API and collection triggers."""

from __future__ import annotations

from flask import Blueprint, abort, jsonify, request
from sqlalchemy import or_

from ..collectors.ats.base import make_client
from ..employers.detection import (
    discover_employer,
    discover_pending,
    normalize_domain,
    valid_domain,
)
from ..employers.service import (
    collect_employer,
    collect_ready,
    employer_stats,
    seed_employers,
)
from ..errors import ValidationError
from ..extensions import db
from ..models import EmployerSource, Offer
from ..models import Campaign
from ..serializers import (
    employer_to_dict,
    offer_summary_to_dict,
    offer_to_dict,
)
from ..validation import Validator, request_payload


def _bounded_int(raw: object, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return min(max(value, minimum), maximum)


def create_employers_blueprint() -> Blueprint:
    bp = Blueprint("employers", __name__)

    @bp.get("/employers")
    def list_employers():
        query = EmployerSource.query
        status = request.args.get("status", "").strip()
        if status:
            query = query.filter(EmployerSource.status == status)
        enabled = request.args.get("enabled", "").strip().lower()
        if enabled in {"true", "false"}:
            query = query.filter(EmployerSource.enabled.is_(enabled == "true"))

        limit = _bounded_int(request.args.get("limit"), 300, 1, 500)
        employers = (
            query.order_by(EmployerSource.status.asc(), EmployerSource.name.asc())
            .limit(limit)
            .all()
        )

        return jsonify(
            {
                "employers": [employer_to_dict(employer) for employer in employers],
                "stats": employer_stats(),
            }
        )

    @bp.post("/employers")
    def create_employer():
        data = Validator(request_payload())
        domain_input = data.text("domain", "Domaine", max_length=255, required=True)
        careers_url = data.text("careers_url", "URL carrières", max_length=700)
        name = data.text("name", "Nom", max_length=200)
        data.finish()

        domain = normalize_domain(domain_input)
        if not valid_domain(domain):
            raise ValidationError(
                "Domaine invalide.",
                fields={"domain": "Indique un domaine valide, par exemple mistral.ai."},
            )

        employer = EmployerSource.query.filter_by(domain=domain).one_or_none()
        created = employer is None

        if created:
            employer = EmployerSource(
                name=name or domain.split(".")[0].replace("-", " ").title(),
                domain=domain,
                sector="IA",
                country="FR",
                careers_url=careers_url,
                origin="manual",
                status="pending",
            )
            db.session.add(employer)
            db.session.commit()
        else:
            if name:
                employer.name = name
            if careers_url:
                employer.careers_url = careers_url
            db.session.commit()

        if employer.careers_url and not employer.ats_type:
            discover_employer(employer)

        return (
            jsonify(
                {
                    "employer": employer_to_dict(employer),
                    "created": created,
                }
            ),
            201 if created else 200,
        )

    @bp.patch("/employers/<int:employer_id>")
    def update_employer(employer_id: int):
        employer = db.session.get(EmployerSource, employer_id)
        if employer is None:
            abort(404, description="Employeur introuvable.")

        data = Validator(request_payload())
        name = data.text("name", "Nom", max_length=200)
        careers_url = data.text("careers_url", "URL carrières", max_length=700)
        enabled = data.boolean("enabled", employer.enabled)
        data.finish()

        if name:
            employer.name = name
        if careers_url and careers_url != employer.careers_url:
            employer.careers_url = careers_url
            employer.ats_type = ""
            employer.ats_slug = ""
            employer.status = "pending"
        employer.enabled = enabled
        db.session.commit()

        if employer.careers_url and not employer.ats_type and employer.enabled:
            discover_employer(employer)

        return jsonify({"employer": employer_to_dict(employer)})

    @bp.post("/employers/seed")
    def seed():
        summary = seed_employers()
        return jsonify({"seed": summary, "stats": employer_stats()})

    @bp.post("/employers/discover")
    def discover():
        data = Validator(request_payload())
        limit = data.integer("limit", "Limite", minimum=1, maximum=25, default=8)
        data.finish()

        summary = discover_pending(limit=limit)
        return jsonify({"discovery": summary, "stats": employer_stats()})

    @bp.post("/employers/collect")
    def collect():
        data = Validator(request_payload())
        limit = data.integer("limit", "Limite", minimum=1, maximum=25, default=5)
        max_offers = data.integer(
            "max_offers", "Offres par employeur", minimum=1, maximum=200, default=50
        )
        data.finish()

        summary = collect_ready(limit=limit, max_offers=max_offers)
        return jsonify({"collection": summary, "stats": employer_stats()})

    @bp.post("/employers/<int:employer_id>/collect")
    def collect_one(employer_id: int):
        employer = db.session.get(EmployerSource, employer_id)
        if employer is None:
            abort(404, description="Employeur introuvable.")

        with make_client() as client:
            result = collect_employer(employer, client=client, max_offers=50)

        return jsonify(
            {"collection": result, "employer": employer_to_dict(employer)}
        )

    @bp.get("/offers")
    def list_offers():
        query = Offer.query.filter(Offer.deleted_at.is_(None))
        campaign = Campaign.get_current()
        campaign_filter = request.args.get("campaign", "").lower() in {"1", "true", "yes"}

        if campaign_filter:
            if campaign.keywords:
                keyword_filters = []
                for keyword in campaign.keywords:
                    pattern = f"%{keyword}%"
                    keyword_filters.append(Offer.title.ilike(pattern))
                    keyword_filters.append(Offer.description.ilike(pattern))
                query = query.filter(or_(*keyword_filters))

            if campaign.locations:
                query = query.filter(
                    or_(*[Offer.location.ilike(f"%{location}%") for location in campaign.locations])
                )

            if campaign.remote != "any":
                query = query.filter(Offer.remote == campaign.remote)

        employer_id = request.args.get("employer_id")
        if employer_id:
            query = query.filter(Offer.employer_id == _bounded_int(employer_id, 0, 0, 10**9))
        remote = request.args.get("remote", "").strip()
        if remote:
            query = query.filter(Offer.remote == remote)
        search = request.args.get("q", "").strip()
        if search:
            query = query.filter(Offer.title.ilike(f"%{search}%"))

        limit = _bounded_int(request.args.get("limit"), 50, 1, 200)
        offset = _bounded_int(request.args.get("offset"), 0, 0, 10**6)
        offers = (
            query.order_by(Offer.published_at.desc(), Offer.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return jsonify(
            {
                "offers": [offer_summary_to_dict(offer) for offer in offers],
                "total": query.count(),
                "campaign_filter": {
                    "active": campaign_filter,
                    "keywords": list(campaign.keywords or []),
                    "locations": list(campaign.locations or []),
                    "remote": campaign.remote,
                },
            }
        )

    @bp.get("/offers/<int:offer_id>")
    def get_offer(offer_id: int):
        offer = db.session.get(Offer, offer_id)
        if offer is None:
            abort(404, description="Offre introuvable.")
        return jsonify({"offer": offer_to_dict(offer)})

    return bp
