"""Shared helpers for ATS collectors.

Employer ATS feeds are public JSON APIs. They are more stable than HTML
scraping and usually expose the employer's own application URL, which is
exactly what this project wants to keep.
"""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Protocol

import httpx

USER_AGENT = "JobFinder/0.1 (personal job search; local application)"
MAX_DESCRIPTION_CHARS = 40_000


class AtsError(Exception):
    """The ATS refused or failed the request."""


class AtsNotFound(AtsError):
    """The slug does not exist on this ATS."""


@dataclass(frozen=True)
class CollectedOffer:
    external_id: str
    title: str
    location: str
    description: str
    apply_url: str
    source_url: str
    published_at: datetime | None = None
    company: str = ""
    remote: str = ""
    contract_type: str = ""
    salary: str = ""


class AtsAdapter(Protocol):
    name: str

    def detect_url(self, url: str) -> str | None: ...
    def fetch(
        self, client: httpx.Client, slug: str, *, limit: int = 100
    ) -> list[CollectedOffer]: ...
    def probe(self, client: httpx.Client, slug: str) -> bool: ...


def get_json(
    client: httpx.Client, url: str, *, params: dict[str, Any] | None = None
) -> Any:
    response = client.get(url, params=params)
    if response.status_code == 404:
        raise AtsNotFound(f"Not found: {url}")
    if response.status_code >= 400:
        raise AtsError(f"HTTP {response.status_code} for {url}")
    try:
        return response.json()
    except ValueError as error:
        raise AtsError(f"Non-JSON response from {url}") from error


class _TextExtractor(HTMLParser):
    BLOCK_TAGS = {
        "br", "p", "div", "li", "ul", "ol", "tr", "td", "th",
        "h1", "h2", "h3", "h4", "h5", "h6", "section", "article",
    }

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def html_to_text(value: str | None) -> str:
    """Convert HTML (sometimes double-escaped by an API) to readable text."""
    if not value:
        return ""

    text = value
    # Greenhouse returns "&lt;div&gt;..." and some feeds return real HTML.
    if "&lt;" in text or "&gt;" in text:
        text = html_lib.unescape(text)

    if "<" in text and ">" in text:
        parser = _TextExtractor()
        parser.feed(text)
        text = "".join(parser.parts)
    else:
        text = html_lib.unescape(text)

    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:MAX_DESCRIPTION_CHARS]


def parse_datetime(value: object) -> datetime | None:
    if value is None or value == "":
        return None

    if isinstance(value, (int, float)):
        # Lever uses milliseconds; other feeds use seconds.
        seconds = value / 1000 if value > 10_000_000_000 else value
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    if not isinstance(value, str):
        return None

    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def normalize_remote(*values: object) -> str:
    for value in values:
        if isinstance(value, bool):
            if value:
                return "remote"
            continue
        if not isinstance(value, str):
            continue
        text = value.strip().lower()
        if not text:
            continue
        if "hybrid" in text or "hybride" in text:
            return "hybrid"
        if "remote" in text or "télétravail" in text or "teletravail" in text:
            return "remote"
        if "on-site" in text or "onsite" in text or "sur site" in text:
            return "onsite"
    return ""


def join_locations(values: list[str]) -> str:
    seen: list[str] = []
    for value in values:
        cleaned = " ".join(str(value).split())
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return ", ".join(seen[:4])


def make_client() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(20.0),
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
