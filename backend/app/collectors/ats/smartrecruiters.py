"""SmartRecruiters job board API.

The list endpoint does not include the description, so `fetch` also requests
the detail of each posting. Collection therefore passes a small limit.
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

NAME = "smartrecruiters"
LIST_API = "https://api.smartrecruiters.com/v1/companies/{slug}/postings"
DETAIL_API = "https://api.smartrecruiters.com/v1/companies/{slug}/postings/{id}"
PUBLIC_URL = "https://jobs.smartrecruiters.com/{slug}/{id}"
URL_RE = re.compile(
    r"https?://(?:jobs|careers)\.smartrecruiters\.com/([^/?#]+)", re.IGNORECASE
)


def detect_url(url: str) -> str | None:
    match = URL_RE.search(url)
    return match.group(1) if match else None


def fetch(
    client: httpx.Client, slug: str, *, limit: int = 100
) -> list[CollectedOffer]:
    data = get_json(client, LIST_API.format(slug=slug), params={"limit": limit})
    content = data.get("content") if isinstance(data, dict) else None
    if not isinstance(content, list):
        raise AtsError("Réponse SmartRecruiters inattendue.")

    offers: list[CollectedOffer] = []
    for item in content[:limit]:
        if not isinstance(item, dict):
            continue
        posting_id = str(item.get("id") or "")
        location = item.get("location") or {}
        company = (item.get("company") or {}).get("name") or ""
        description = _fetch_description(client, slug, posting_id)
        public_url = PUBLIC_URL.format(slug=slug, id=posting_id)

        offers.append(
            CollectedOffer(
                external_id=posting_id,
                title=str(item.get("name") or ""),
                company=str(company),
                location=join_locations(
                    [
                        str(location.get("fullLocation") or ""),
                        str(location.get("city") or ""),
                        str(location.get("country") or ""),
                    ]
                ),
                description=description,
                apply_url=public_url,
                source_url=public_url,
                published_at=parse_datetime(item.get("releasedDate")),
                remote=normalize_remote(
                    location.get("remote"), location.get("hybrid")
                ),
                contract_type=str(
                    (item.get("typeOfEmployment") or {}).get("label") or ""
                ),
            )
        )
    return offers


def _fetch_description(client: httpx.Client, slug: str, posting_id: str) -> str:
    if not posting_id:
        return ""
    try:
        detail = get_json(
            client, DETAIL_API.format(slug=slug, id=posting_id)
        )
    except (AtsError, httpx.HTTPError):
        return ""

    job_ad = detail.get("jobAd") if isinstance(detail, dict) else None
    sections = job_ad.get("sections") if isinstance(job_ad, dict) else None
    if not isinstance(sections, list):
        return ""

    parts = [
        html_to_text(section.get("text"))
        for section in sections
        if isinstance(section, dict)
    ]
    return "\n\n".join(part for part in parts if part)


def probe(client: httpx.Client, slug: str) -> bool:
    try:
        data = get_json(
            client, LIST_API.format(slug=slug), params={"limit": 1}
        )
        return bool(isinstance(data, dict) and int(data.get("totalFound") or 0) > 0)
    except (AtsError, httpx.HTTPError, ValueError):
        return False
