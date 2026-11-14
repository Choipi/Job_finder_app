"""Greenhouse job board API.

Endpoint: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
`content=true` includes the full HTML description, so it can be large.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

import httpx

from .base import (
    AtsError,
    CollectedOffer,
    get_json,
    html_to_text,
    normalize_remote,
    parse_datetime,
)

NAME = "greenhouse"
API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
URL_RE = re.compile(
    r"https?://(?:job-boards|boards)\.greenhouse\.io/([^/?#]+)", re.IGNORECASE
)


def detect_url(url: str) -> str | None:
    match = URL_RE.search(url)
    if match:
        slug = match.group(1)
        if slug != "embed":
            return slug

    # Embed form: boards.greenhouse.io/embed/job_board?for=company
    parsed = urlparse(url)
    if "greenhouse.io" in parsed.netloc:
        slug = parse_qs(parsed.query).get("for", [None])[0]
        if slug:
            return slug
    return None


def fetch(
    client: httpx.Client, slug: str, *, limit: int = 100
) -> list[CollectedOffer]:
    data = get_json(
        client, API.format(slug=slug), params={"content": "true"}
    )
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, list):
        raise AtsError("Réponse Greenhouse inattendue.")

    offers: list[CollectedOffer] = []
    for job in jobs[:limit]:
        if not isinstance(job, dict):
            continue
        metadata = {
            str(item.get("name", "")).lower(): item.get("value")
            for item in job.get("metadata") or []
            if isinstance(item, dict)
        }
        offers.append(
            CollectedOffer(
                external_id=str(job.get("id") or ""),
                title=str(job.get("title") or ""),
                company=str(job.get("company_name") or ""),
                location=str((job.get("location") or {}).get("name") or ""),
                description=html_to_text(job.get("content")),
                apply_url=str(job.get("absolute_url") or ""),
                source_url=str(job.get("absolute_url") or ""),
                published_at=parse_datetime(
                    job.get("first_published") or job.get("updated_at")
                ),
                remote=normalize_remote(metadata.get("location type")),
                contract_type=str(
                    metadata.get("employment type")
                    or metadata.get("contract type")
                    or ""
                ),
            )
        )
    return offers


def probe(client: httpx.Client, slug: str) -> bool:
    try:
        data = get_json(
            client, API.format(slug=slug), params={"content": "false"}
        )
        return bool(isinstance(data, dict) and data.get("jobs"))
    except (AtsError, httpx.HTTPError):
        return False
