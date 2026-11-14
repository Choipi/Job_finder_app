"""Discover which ATS an employer uses.

Strategy, in order:

1. if the careers URL already points at a known ATS, read the slug from it;
2. fetch the company site and its common careers paths, then look for an ATS
   link in the HTML (this is how Mistral AI is detected: Ashby slug `mistral.ai`);
3. as a last resort, probe a few guessed slugs against the ATS APIs.

Discovery is deliberately bounded: a batch handles a small number of
employers, with delays, so the app never hammers a site.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from ..collectors.ats import ADAPTERS
from ..collectors.ats.base import USER_AGENT
from ..extensions import db
from ..models import EmployerSource

CAREER_PATHS = (
    "/careers",
    "/jobs",
    "/carrieres",
    "/nous-rejoindre",
    "/recrutement",
    "/join-us",
)

PROBE_ORDER = ("ashby", "lever", "greenhouse", "workable", "smartrecruiters")


from typing import NamedTuple

...

class Detection(NamedTuple):
    ats_type: str
    ats_slug: str


@dataclass(frozen=True)
class DiscoveryResult:
    employer_id: int
    name: str
    status: str
    ats_type: str = ""
    ats_slug: str = ""
    error: str = ""


def normalize_domain(value: str) -> str:
    """Accept `example.com`, `https://www.example.com/careers`, etc."""
    text = value.strip().lower()
    if not text:
        return ""
    if "://" not in text:
        text = f"https://{text}"
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def valid_domain(domain: str) -> bool:
    return bool(domain) and "." in domain and " " not in domain and len(domain) <= 255


def guess_slugs(domain: str, name: str = "") -> list[str]:
    base = domain.split(".")[0]
    candidates = [
        domain,
        domain.rsplit(".", 1)[0],
        base,
        base.replace("-", ""),
        "".join(ch for ch in name.lower() if ch.isalnum()),
    ]
    seen: list[str] = []
    for value in candidates:
        cleaned = value.strip().strip(".")
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen


def detect_from_url(url: str) -> Detection | None:
    for ats_type, adapter in ADAPTERS.items():
        slug = adapter.detect_url(url)
        if slug:
            return Detection(ats_type=ats_type, ats_slug=slug)
    return None


def careers_url_for(ats_type: str, slug: str) -> str:
    return {
        "ashby": f"https://jobs.ashbyhq.com/{slug}",
        "lever": f"https://jobs.lever.co/{slug}",
        "greenhouse": f"https://job-boards.greenhouse.io/{slug}",
        "smartrecruiters": f"https://jobs.smartrecruiters.com/{slug}",
        "workable": f"https://apply.workable.com/{slug}/",
    }.get(ats_type, "")


def _browser_client() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(15.0),
        follow_redirects=True,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        },
    )


def discover_employer(
    employer: EmployerSource,
    *,
    client: httpx.Client | None = None,
    max_probes: int = 4,
) -> DiscoveryResult:
    own_client = client is None
    browser = client or _browser_client()
    checked = 0
    failures: list[str] = []

    try:
        if employer.careers_url:
            direct = detect_from_url(employer.careers_url)
            if direct:
                return _apply_detection(employer, direct, checked)

        pages: list[str] = []
        if employer.careers_url:
            pages.append(employer.careers_url)
        base = f"https://{employer.domain}"
        pages.append(base)
        pages.extend(f"{base}{path}" for path in CAREER_PATHS)

        for page in pages[:5]:
            checked += 1
            try:
                response = browser.get(page)
            except httpx.HTTPError as error:
                failures.append(type(error).__name__)
                continue

            if response.status_code >= 400:
                failures.append(f"HTTP {response.status_code}")
                continue

            found = detect_from_url(str(response.url)) or detect_from_url(response.text)
            if found:
                return _apply_detection(employer, found, checked)
            time.sleep(0.5)

        probes = 0
        for ats_type in PROBE_ORDER:
            adapter = ADAPTERS[ats_type]
            for slug in guess_slugs(employer.domain, employer.name)[:2]:
                if probes >= max_probes:
                    break
                probes += 1
                try:
                    if adapter.probe(browser, slug):
                        return _apply_detection(
                            employer,
                            Detection(ats_type=ats_type, ats_slug=slug),
                            checked,
                        )
                except Exception:  # noqa: BLE001 - a probe must never break a batch
                    failures.append(f"{ats_type}:probe")
                time.sleep(0.3)
            if probes >= max_probes:
                break

        employer.last_checked_at = datetime.now(timezone.utc)
        if checked == 0 or (failures and checked <= len(failures)):
            employer.status = "error"
            employer.last_error = ", ".join(failures[-3:])[:500]
        else:
            employer.status = "no_ats"
            employer.last_error = ""
        db.session.commit()
        return DiscoveryResult(
            employer_id=employer.id,
            name=employer.name,
            status=employer.status,
            error=employer.last_error,
        )
    finally:
        if own_client:
            browser.close()


def _apply_detection(
    employer: EmployerSource, detection: Detection, checked: int
) -> DiscoveryResult:
    employer.ats_type = detection.ats_type
    employer.ats_slug = detection.ats_slug
    employer.careers_url = employer.careers_url or careers_url_for(
        detection.ats_type, detection.ats_slug
    )
    employer.status = "ready"
    employer.last_error = ""
    employer.last_checked_at = datetime.now(timezone.utc)
    db.session.commit()
    return DiscoveryResult(
        employer_id=employer.id,
        name=employer.name,
        status="ready",
        ats_type=employer.ats_type,
        ats_slug=employer.ats_slug,
    )


def discover_pending(limit: int = 8) -> dict[str, object]:
    """Detect ATS for a bounded batch of pending/error employers."""
    employers = (
        EmployerSource.query.filter(
            EmployerSource.enabled.is_(True),
            EmployerSource.status.in_(("pending", "error")),
        )
        .order_by(EmployerSource.last_checked_at.asc().nullsfirst())
        .limit(limit)
        .all()
    )

    results: list[DiscoveryResult] = []
    browser = _browser_client()
    try:
        for employer in employers:
            results.append(discover_employer(employer, client=browser))
            time.sleep(0.8)
    finally:
        browser.close()

    return {
        "checked": len(results),
        "ready": sum(1 for result in results if result.status == "ready"),
        "no_ats": sum(1 for result in results if result.status == "no_ats"),
        "errors": sum(1 for result in results if result.status == "error"),
        "results": [
            {
                "id": result.employer_id,
                "name": result.name,
                "status": result.status,
                "ats_type": result.ats_type,
                "ats_slug": result.ats_slug,
                "error": result.error,
            }
            for result in results
        ],
    }
