"""Lever job board API.

Endpoint: https://api.lever.co/v0/postings/{slug}?mode=json
"""

from __future__ import annotations

import re

import httpx

from .base import (
    AtsError,
    CollectedOffer,
    get_json,
    html_to_text,
    normalize_remote,
    parse_datetime,
)

NAME = "lever"
API = "https://api.lever.co/v0/postings/{slug}"
URL_RE = re.compile(r"https?://jobs\.lever\.co/([^/?#]+)", re.IGNORECASE)


def detect_url(url: str) -> str | None:
    match = URL_RE.search(url)
    return match.group(1) if match else None


def fetch(
    client: httpx.Client, slug: str, *, limit: int = 100
) -> list[CollectedOffer]:
    data = get_json(client, API.format(slug=slug), params={"mode": "json"})
    if not isinstance(data, list):
        raise AtsError("Réponse Lever inattendue.")

    offers: list[CollectedOffer] = []
    for job in data[:limit]:
        if not isinstance(job, dict):
            continue
        categories = job.get("categories") or {}
        description = "\n\n".join(
            part
            for part in [
                html_to_text(job.get("description")),
                html_to_text(job.get("additional")),
            ]
            if part
        )
        offers.append(
            CollectedOffer(
                external_id=str(job.get("id") or ""),
                title=str(job.get("text") or ""),
                location=str(categories.get("location") or ""),
                description=description,
                apply_url=str(job.get("applyUrl") or job.get("hostedUrl") or ""),
                source_url=str(job.get("hostedUrl") or job.get("applyUrl") or ""),
                published_at=parse_datetime(job.get("createdAt")),
                remote=normalize_remote(job.get("workplaceType")),
                contract_type=str(categories.get("commitment") or ""),
            )
        )
    return offers


def probe(client: httpx.Client, slug: str) -> bool:
    try:
        return bool(fetch(client, slug, limit=1))
    except (AtsError, httpx.HTTPError):
        return False
