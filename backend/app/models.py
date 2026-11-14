"""Database models.

Phase 2 stores exactly two singletons: the user profile and the current
campaign. Offers, scans and the blacklist arrive in later phases.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from .extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Profile(db.Model):
    __tablename__ = "profile"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False, default="")
    last_name = db.Column(db.String(80), nullable=False, default="")
    email = db.Column(db.String(180), nullable=False, default="")
    phone = db.Column(db.String(40), nullable=False, default="")
    city = db.Column(db.String(120), nullable=False, default="")
    headline = db.Column(db.String(160), nullable=False, default="")
    summary = db.Column(db.Text, nullable=False, default="")

    # CV: file on disk, extracted text in DB (editable by the user).
    cv_path = db.Column(db.String(500), nullable=False, default="")
    cv_filename = db.Column(db.String(255), nullable=False, default="")
    cv_text = db.Column(db.Text, nullable=False, default="")
    cv_uploaded_at = db.Column(db.DateTime(timezone=True), nullable=True)

    letter_template = db.Column(db.Text, nullable=False, default="")

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    @classmethod
    def get_current(cls) -> "Profile":
        """Return the singleton profile, creating it on first access."""
        profile = db.session.get(cls, 1)
        if profile is None:
            profile = cls(id=1)
            db.session.add(profile)
            db.session.commit()
        return profile


class Campaign(db.Model):
    __tablename__ = "campaign"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, default="Ma recherche")

    # Search criteria, stored as JSON arrays to keep SQLite simple.
    keywords = db.Column(db.JSON, nullable=False, default=list)
    locations = db.Column(db.JSON, nullable=False, default=list)
    contract_types = db.Column(db.JSON, nullable=False, default=lambda: ["CDI"])
    remote = db.Column(db.String(20), nullable=False, default="any")
    radius_km = db.Column(db.Integer, nullable=False, default=30)

    # Collection settings.
    sources = db.Column(
        db.JSON,
        nullable=False,
        default=list,
    )
    starts_on = db.Column(db.Date, nullable=True)
    ends_on = db.Column(db.Date, nullable=True)
    frequency_hours = db.Column(db.Integer, nullable=False, default=6)
    is_paused = db.Column(db.Boolean, nullable=False, default=False)

    # Display filter only: the UI shows every offer by default.
    score_threshold = db.Column(db.Integer, nullable=False, default=0)

    # Per-task model choice, falling back to the values from .env.
    scoring_model = db.Column(db.String(120), nullable=False, default="")
    letter_model = db.Column(db.String(120), nullable=False, default="")

    last_scan_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    @classmethod
    def get_current(cls) -> "Campaign":
        """Return the single campaign, creating a sensible default once."""
        campaign = db.session.get(cls, 1)
        if campaign is None:
            today = date.today()
            campaign = cls(
                id=1,
                name="Ma recherche",
                keywords=[],
                locations=[],
                contract_types=["CDI"],
                remote="any",
                radius_km=30,
                sources=[],
                starts_on=today,
                ends_on=today + timedelta(days=30),
                frequency_hours=6,
                score_threshold=0,
            )
            db.session.add(campaign)
            db.session.commit()
        return campaign

    @property
    def status(self) -> str:
        """Derived state, never stored: one source of truth."""
        if self.is_paused:
            return "paused"
        if self.starts_on is None or self.ends_on is None:
            return "draft"
        today = date.today()
        if today < self.starts_on:
            return "scheduled"
        if today > self.ends_on:
            return "finished"
        return "active"

    @property
    def days_remaining(self) -> int | None:
        if self.ends_on is None:
            return None
        return max((self.ends_on - date.today()).days, 0)


class GeneratedLetter(db.Model):
    __tablename__ = "generated_letter"

    id = db.Column(db.Integer, primary_key=True)

    # Snapshot of the offer: a letter must stay readable even if the offer
    # is later deleted or never stored (phase 3 has no offers yet).
    job_title = db.Column(db.String(200), nullable=False, default="")
    company = db.Column(db.String(200), nullable=False, default="")
    source_url = db.Column(db.String(500), nullable=False, default="")
    job_description = db.Column(db.Text, nullable=False, default="")
    instructions = db.Column(db.Text, nullable=False, default="")

    subject = db.Column(db.String(300), nullable=False, default="")
    body = db.Column(db.Text, nullable=False, default="")
    offer_id = db.Column(db.Integer, nullable=True, index=True)

    model = db.Column(db.String(120), nullable=False, default="")
    prompt_version = db.Column(db.String(40), nullable=False, default="")
    prompt_tokens = db.Column(db.Integer, nullable=False, default=0)
    completion_tokens = db.Column(db.Integer, nullable=False, default=0)
    cost_usd = db.Column(db.Float, nullable=False, default=0.0)
    duration_ms = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class LLMCall(db.Model):
    __tablename__ = "llm_call"

    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(40), nullable=False, default="")
    model = db.Column(db.String(120), nullable=False, default="")
    prompt_version = db.Column(db.String(40), nullable=False, default="")
    status = db.Column(db.String(20), nullable=False, default="ok")
    prompt_tokens = db.Column(db.Integer, nullable=False, default=0)
    completion_tokens = db.Column(db.Integer, nullable=False, default=0)
    cost_usd = db.Column(db.Float, nullable=False, default=0.0)
    duration_ms = db.Column(db.Integer, nullable=False, default=0)
    error = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class EmployerSource(db.Model):
    """An employer whose careers/ATS feed is polled directly.

    A source is discovered one of three ways:
    - seeded from a curated list (AI France for the test watchlist),
    - added manually by the user,
    - detected from an aggregator's apply_url in a later phase.
    """

    __tablename__ = "employer_source"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, default="")
    domain = db.Column(db.String(255), nullable=False, unique=True, index=True)
    sector = db.Column(db.String(80), nullable=False, default="")
    country = db.Column(db.String(2), nullable=False, default="FR")
    city = db.Column(db.String(120), nullable=False, default="")

    ats_type = db.Column(db.String(40), nullable=False, default="")
    ats_slug = db.Column(db.String(200), nullable=False, default="")
    careers_url = db.Column(db.String(700), nullable=False, default="")

    enabled = db.Column(db.Boolean, nullable=False, default=True)
    origin = db.Column(db.String(30), nullable=False, default="manual")
    # pending | ready | no_ats | error
    status = db.Column(db.String(20), nullable=False, default="pending")
    last_checked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_error = db.Column(db.String(500), nullable=False, default="")
    offer_count = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class Offer(db.Model):
    """Normalized job offer.

    The fingerprint is the deduplication key across sources. In phase 4 all
    offers come from employer ATS feeds; job boards will reuse the same table.
    """

    __tablename__ = "offer"

    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(
        db.Integer, db.ForeignKey("employer_source.id"), nullable=True, index=True
    )

    source = db.Column(db.String(40), nullable=False, default="employer_ats")
    external_id = db.Column(db.String(200), nullable=False, default="")
    title = db.Column(db.String(300), nullable=False, default="")
    company = db.Column(db.String(200), nullable=False, default="")
    location = db.Column(db.String(200), nullable=False, default="")
    remote = db.Column(db.String(20), nullable=False, default="")
    contract_type = db.Column(db.String(80), nullable=False, default="")
    salary = db.Column(db.String(120), nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")

    source_url = db.Column(db.String(700), nullable=False, default="")
    apply_url = db.Column(db.String(700), nullable=False, default="")
    published_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=True)

    fingerprint = db.Column(db.String(64), nullable=False, unique=True, index=True)
    status = db.Column(db.String(20), nullable=False, default="new")
    score = db.Column(db.Integer, nullable=True)
    score_reasons = db.Column(db.JSON, nullable=False, default=list)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    score_record = db.relationship(
        "OfferScore",
        back_populates="offer",
        uselist=False,
        cascade="all, delete-orphan",
    )


class OfferScore(db.Model):
    """Latest LLM evaluation of an offer.

    Kept in a separate table so the scoring prompt version, model and error are
    auditable without mixing them with the application status of the offer.
    """

    __tablename__ = "offer_score"

    id = db.Column(db.Integer, primary_key=True)
    offer_id = db.Column(
        db.Integer, db.ForeignKey("offer.id"), nullable=False, unique=True, index=True
    )
    status = db.Column(db.String(20), nullable=False, default="scored")
    score = db.Column(db.Integer, nullable=True)
    reasons = db.Column(db.JSON, nullable=False, default=list)
    blockers = db.Column(db.JSON, nullable=False, default=list)
    model = db.Column(db.String(120), nullable=False, default="")
    prompt_version = db.Column(db.String(40), nullable=False, default="")
    error = db.Column(db.String(500), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    offer = db.relationship("Offer", back_populates="score_record")


class OfferBlacklist(db.Model):
    """Fingerprints the user explicitly deleted; never re-imported."""

    __tablename__ = "offer_blacklist"

    id = db.Column(db.Integer, primary_key=True)
    fingerprint = db.Column(db.String(64), nullable=False, unique=True, index=True)
    reason = db.Column(db.String(200), nullable=False, default="deleted_by_user")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class ScanRun(db.Model):
    """One collection + scoring pass, manual or scheduled."""

    __tablename__ = "scan_run"

    id = db.Column(db.Integer, primary_key=True)
    trigger = db.Column(db.String(20), nullable=False, default="manual")
    status = db.Column(db.String(20), nullable=False, default="running")
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)
    employers_checked = db.Column(db.Integer, nullable=False, default=0)
    offers_found = db.Column(db.Integer, nullable=False, default=0)
    offers_new = db.Column(db.Integer, nullable=False, default=0)
    offers_scored = db.Column(db.Integer, nullable=False, default=0)
    errors = db.Column(db.Integer, nullable=False, default=0)
    detail = db.Column(db.JSON, nullable=False, default=dict)
