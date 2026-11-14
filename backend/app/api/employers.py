"""Employer watchlist API and collection triggers."""

from __future__ import annotations

from datetime import datetime, timezone

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
    offer_fingerprint,
    seed_employers,
)
from ..errors import ValidationError
from ..extensions import db
from ..models import Campaign, EmployerSource, Offer, OfferBlacklist
from ..scoring.service import score_offers
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
        status = request.args.get("status", "").strip()
        if status:
            query = query.filter(Offer.status == status)
        min_score = request.args.get("min_score")
        if min_score not in (None, ""):
            query = query.filter(Offer.score >= _bounded_int(min_score, 0, 0, 100))

        if request.args.get("sort") == "score":
            query = query.order_by(
                Offer.score.desc(), Offer.published_at.desc(), Offer.id.desc()
            )
        else:
            query = query.order_by(Offer.published_at.desc(), Offer.id.desc())

        offers = query.offset(offset).limit(limit).all()

        return jsonify(
            {
                "offers": [offer_summary_to_dict(offer) for offer in offers],
                "total": query.count(),
                "stats": {
                    "total": Offer.query.filter(Offer.deleted_at.is_(None)).count(),
                    "scored": Offer.query.filter(
                        Offer.deleted_at.is_(None), Offer.score.isnot(None)
                    ).count(),
                    "applied": Offer.query.filter(
                        Offer.deleted_at.is_(None), Offer.status == "applied"
                    ).count(),
                },
                "campaign_filter": {
                    "active": campaign_filter,
                    "keywords": list(campaign.keywords or []),
                    "locations": list(campaign.locations or []),
                    "remote": campaign.remote,
                },
            }
        )

    @bp.post("/offers")
    def create_manual_offer():
        data = Validator(request_payload())
        values = {
            "title": data.text("title", "Intitulé", max_length=300, required=True),
            "company": data.text("company", "Entreprise", max_length=200, required=True),
            "location": data.text("location", "Lieu", max_length=200),
            "source_url": data.text("source_url", "Lien de l’annonce", max_length=700),
            "contract_type": data.text("contract_type", "Contrat", max_length=80),
            "remote": data.choice(
                "remote",
                "Télétravail",
                ("", "remote", "hybrid", "onsite"),
                default="",
            ),
            "description": data.text(
                "description", "Texte de l’offre", max_length=30_000, required=True
            ),
        }
        if values["description"] and len(values["description"]) < 40:
            data.add_error(
                "description",
                "Le texte de l’offre doit contenir au moins 40 caractères.",
            )
        data.finish()

        title = " ".join(values["title"].split())
        company = " ".join(values["company"].split())
        location = " ".join(values["location"].split())
        description = values["description"]
        source_url = values["source_url"]
        fingerprint = offer_fingerprint(title, company, location)

        existing = Offer.query.filter_by(fingerprint=fingerprint).one_or_none()
        if existing is not None:
            # An explicit manual add wins over a previous deletion.
            existing.deleted_at = None
            OfferBlacklist.query.filter_by(fingerprint=fingerprint).delete()
            if existing.source == "manual":
                existing.location = location
                existing.source_url = source_url
                existing.apply_url = source_url
                existing.contract_type = values["contract_type"]
                existing.remote = values["remote"]
                existing.description = description
            db.session.commit()
            return jsonify({"offer": offer_to_dict(existing), "created": False})

        offer = Offer(
            source="manual",
            title=title,
            company=company,
            location=location,
            remote=values["remote"],
            contract_type=values["contract_type"],
            description=description,
            source_url=source_url,
            apply_url=source_url,
            fingerprint=fingerprint,
            status="new",
        )
        db.session.add(offer)
        db.session.commit()

        return jsonify({"offer": offer_to_dict(offer), "created": True}), 201

    @bp.post("/offers/score")
    def score_offers_endpoint():
        data = Validator(request_payload())
        limit = data.integer("limit", "Limite", minimum=1, maximum=50, default=20)
        data.finish()

        summary = score_offers(limit=limit)
        return jsonify({"scoring": summary})

    @bp.patch("/offers/<int:offer_id>")
    def update_offer(offer_id: int):
        offer = db.session.get(Offer, offer_id)
        if offer is None or offer.deleted_at is not None:
            abort(404, description="Offre introuvable.")

        data = Validator(request_payload())
        status = data.choice(
            "status",
            "Statut",
            ("new", "to_apply", "applied", "interview", "rejected"),
            default=offer.status,
        )
        data.finish()

        offer.status = status
        db.session.commit()
        return jsonify({"offer": offer_to_dict(offer)})

    @bp.delete("/offers/<int:offer_id>")
    def delete_offer(offer_id: int):
        offer = db.session.get(Offer, offer_id)
        if offer is None or offer.deleted_at is not None:
            abort(404, description="Offre introuvable.")

        offer.deleted_at = datetime.now(timezone.utc)
        if not OfferBlacklist.query.filter_by(fingerprint=offer.fingerprint).first():
            db.session.add(
                OfferBlacklist(
                    fingerprint=offer.fingerprint,
                    reason="deleted_by_user",
                )
            )
        db.session.commit()
        return jsonify({"deleted": True, "offer_id": offer.id})

    @bp.post("/offers/<int:offer_id>/restore")
    def restore_offer(offer_id: int):
        offer = db.session.get(Offer, offer_id)
        if offer is None:
            abort(404, description="Offre introuvable.")

        offer.deleted_at = None
        OfferBlacklist.query.filter_by(fingerprint=offer.fingerprint).delete()
        db.session.commit()
        return jsonify({"offer": offer_to_dict(offer)})

    @bp.get("/offers/<int:offer_id>")
    def get_offer(offer_id: int):
        offer = db.session.get(Offer, offer_id)
        if offer is None or offer.deleted_at is not None:
            abort(404, description="Offre introuvable.")
        return jsonify({"offer": offer_to_dict(offer)})

    return bp
