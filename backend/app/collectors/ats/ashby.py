"""Ashby job board API.

Endpoint: https://api.ashbyhq.com/posting-api/job-board/{slug}
The slug can contain a dot, e.g. `mistral.ai`.
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

NAME = "ashby"
API = "https://api.ashbyhq.com/posting-api/job-board/{slug}"
URL_RE = re.compile(r"https?://jobs\.ashbyhq\.com/([^/?#]+)", re.IGNORECASE)


def detect_url(url: str) -> str | None:
    match = URL_RE.search(url)
    return match.group(1) if match else None


def fetch(
    client: httpx.Client, slug: str, *, limit: int = 100
) -> list[CollectedOffer]:
    data = get_json(client, API.format(slug=slug))
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, list):
        raise AtsError("Réponse Ashby inattendue.")

    offers: list[CollectedOffer] = []
    for job in jobs[:limit]:
        if not isinstance(job, dict) or job.get("isListed") is False:
            continue
        location = job.get("location") or ""
        secondary = [
            item.get("location", "")
            for item in job.get("secondaryLocations") or []
            if isinstance(item, dict)
        ]
        offers.append(
            CollectedOffer(
                external_id=str(job.get("id") or ""),
                title=str(job.get("title") or ""),
                location=join_locations([location, *secondary]),
                description=html_to_text(
                    job.get("descriptionPlain") or job.get("descriptionHtml")
                ),
                apply_url=str(job.get("applyUrl") or job.get("jobUrl") or ""),
                source_url=str(job.get("jobUrl") or job.get("applyUrl") or ""),
                published_at=parse_datetime(job.get("publishedAt")),
                remote=normalize_remote(
                    job.get("isRemote"), job.get("workplaceType")
                ),
                contract_type=str(job.get("employmentType") or ""),
            )
        )
    return offers


def probe(client: httpx.Client, slug: str) -> bool:
    try:
        return bool(fetch(client, slug, limit=1))
    except (AtsError, httpx.HTTPError):
        return False
