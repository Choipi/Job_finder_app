from __future__ import annotations

import httpx

from app.collectors.ats import ashby, greenhouse, lever, smartrecruiters, workable
from app.employers.detection import detect_from_url, guess_slugs, normalize_domain


def client_with(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_ashby_fetch_and_url_detection():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "jobs": [
                    {
                        "id": "a1",
                        "title": "ML Engineer",
                        "location": "Paris",
                        "secondaryLocations": [{"location": "Remote"}],
                        "employmentType": "FullTime",
                        "isRemote": False,
                        "workplaceType": "Hybrid",
                        "jobUrl": "https://jobs.ashbyhq.com/acme/a1",
                        "applyUrl": "https://jobs.ashbyhq.com/acme/a1/application",
                        "descriptionHtml": "<p>Build <b>models</b></p>",
                        "publishedAt": "2026-01-02T03:04:05Z",
                        "isListed": True,
                    }
                ]
            },
        )

    offers = ashby.fetch(client_with(handler), "acme")

    assert len(offers) == 1
    assert offers[0].title == "ML Engineer"
    assert offers[0].location == "Paris, Remote"
    assert offers[0].description == "Build models"
    assert offers[0].remote == "hybrid"
    assert offers[0].apply_url.endswith("/application")
    assert offers[0].published_at is not None
    assert detect_from_url("https://jobs.ashbyhq.com/mistral.ai/123") == (
        "ashby",
        "mistral.ai",
    )


def test_greenhouse_fetch_unescapes_content():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "jobs": [
                    {
                        "id": 2,
                        "title": "Data Scientist",
                        "location": {"name": "Paris"},
                        "content": "&lt;p&gt;Hello &amp; welcome&lt;/p&gt;",
                        "absolute_url": "https://boards.greenhouse.io/acme/jobs/2",
                        "metadata": [{"name": "Location Type", "value": "Remote"}],
                        "first_published": "2026-01-01T00:00:00Z",
                    }
                ]
            },
        )

    offers = greenhouse.fetch(client_with(handler), "acme")

    assert offers[0].description == "Hello & welcome"
    assert offers[0].remote == "remote"
    assert detect_from_url("https://job-boards.greenhouse.io/acme/jobs/2") == (
        "greenhouse",
        "acme",
    )
    assert detect_from_url("https://boards.greenhouse.io/embed/job_board?for=acme") == (
        "greenhouse",
        "acme",
    )


def test_lever_fetch():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "id": "l1",
                    "text": "Backend Engineer",
                    "categories": {"location": "Paris", "commitment": "Full-time"},
                    "description": "<p>Build APIs</p>",
                    "hostedUrl": "https://jobs.lever.co/acme/l1",
                    "applyUrl": "https://jobs.lever.co/acme/l1/apply",
                    "createdAt": 1767225600000,
                    "workplaceType": "remote",
                }
            ],
        )

    offers = lever.fetch(client_with(handler), "acme")

    assert offers[0].title == "Backend Engineer"
    assert offers[0].description == "Build APIs"
    assert offers[0].remote == "remote"
    assert detect_from_url("https://jobs.lever.co/pigment/abc") == ("lever", "pigment")


def test_smartrecruiters_fetch_with_detail():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/postings/4"):
            return httpx.Response(
                200,
                json={
                    "jobAd": {
                        "sections": [{"title": "Mission", "text": "<p>Build AI</p>"}]
                    }
                },
            )
        return httpx.Response(
            200,
            json={
                "totalFound": 1,
                "content": [
                    {
                        "id": "4",
                        "name": "AI Engineer",
                        "company": {"name": "Acme"},
                        "location": {"fullLocation": "Paris, France", "remote": False},
                        "typeOfEmployment": {"label": "Full-time"},
                        "releasedDate": "2026-01-01T00:00:00Z",
                    }
                ],
            },
        )

    offers = smartrecruiters.fetch(client_with(handler), "acme")

    assert offers[0].title == "AI Engineer"
    assert offers[0].company == "Acme"
    assert offers[0].description == "Build AI"
    assert detect_from_url("https://jobs.smartrecruiters.com/acme/4") == (
        "smartrecruiters",
        "acme",
    )


def test_workable_fetch():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "name": "Acme",
                "jobs": [
                    {
                        "title": "MLOps Engineer",
                        "shortcode": "ABC123",
                        "description": "<p>Operate models</p>",
                        "application_url": "https://apply.workable.com/j/ABC123/apply",
                        "url": "https://apply.workable.com/j/ABC123",
                        "published_on": "2026-01-01",
                        "telecommuting": True,
                        "employment_type": "Full-time",
                        "locations": [{"city": "Paris", "country": "France"}],
                    }
                ],
            },
        )

    offers = workable.fetch(client_with(handler), "acme")

    assert offers[0].title == "MLOps Engineer"
    assert offers[0].company == "Acme"
    assert offers[0].remote == "remote"
    assert offers[0].location == "Paris, France"
    assert detect_from_url("https://apply.workable.com/acme/") == ("workable", "acme")


def test_domain_and_slug_helpers():
    assert normalize_domain("https://www.Example.com/careers") == "example.com"
    assert normalize_domain("example.com") == "example.com"
    assert "mistral.ai" in guess_slugs("mistral.ai", "Mistral AI")
    assert "mistral" in guess_slugs("mistral.ai", "Mistral AI")
    assert detect_from_url("https://example.com/careers") is None
