"""Workable job board API.

Endpoint: https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true
"""

from __future__ import annotations

import re

import httpx

from .base import (
    AtsError,
    CollectedOffer,
    get_json,
    html_to_text,
    join_locations,
    normalize_remote,
    parse_datetime,
)

NAME = "workable"
API = "https://apply.workable.com/api/v1/widget/accounts/{slug}"
URL_RE = re.compile(r"https?://apply\.workable\.com/([^/?#]+)", re.IGNORECASE)
SUBDOMAIN_RE = re.compile(r"https?://([^.]+)\.workable\.com", re.IGNORECASE)


def detect_url(url: str) -> str | None:
    match = URL_RE.search(url)
    if match and match.group(1) != "api":
        return match.group(1)
    match = SUBDOMAIN_RE.search(url)
    if match and match.group(1) not in {"www", "apply"}:
        return match.group(1)
    return None


def fetch(
    client: httpx.Client, slug: str, *, limit: int = 100
) -> list[CollectedOffer]:
    data = get_json(
        client, API.format(slug=slug), params={"details": "true"}
    )
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, list):
        raise AtsError("Réponse Workable inattendue.")

    account_name = str(data.get("name") or "")

    offers: list[CollectedOffer] = []
    for job in jobs[:limit]:
        if not isinstance(job, dict):
            continue
        locations = [
            join_locations(
                [
                    str(item.get("city") or ""),
                    str(item.get("country") or ""),
                ]
            )
            for item in job.get("locations") or []
            if isinstance(item, dict)
        ]
        offers.append(
            CollectedOffer(
                external_id=str(job.get("shortcode") or job.get("code") or ""),
                title=str(job.get("title") or ""),
                company=account_name,
                location=join_locations(
                    locations
                    or [
                        str(job.get("city") or ""),
                        str(job.get("country") or ""),
                    ]
                ),
                description=html_to_text(job.get("description")),
                apply_url=str(job.get("application_url") or job.get("url") or ""),
                source_url=str(job.get("url") or ""),
                published_at=parse_datetime(
                    job.get("published_on") or job.get("created_at")
                ),
                remote=normalize_remote(job.get("telecommuting")),
                contract_type=str(job.get("employment_type") or ""),
            )
        )
    return offers


def probe(client: httpx.Client, slug: str) -> bool:
    try:
        data = get_json(
            client, API.format(slug=slug), params={"details": "false"}
        )
        return bool(isinstance(data, dict) and data.get("jobs"))
    except (AtsError, httpx.HTTPError):
        return False
