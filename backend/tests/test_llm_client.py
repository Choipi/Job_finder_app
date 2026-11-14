from __future__ import annotations

import json

import httpx
import pytest

from app.llm.catalog import estimate_cost_usd
from app.llm.client import LLMMessage
from app.llm.errors import LLMTimeout, LLMUpstreamError
from app.llm.opencode_go import OpenCodeGoClient


def make_client(handler, **overrides) -> OpenCodeGoClient:
    options = {
        "base_url": "https://llm.test/v1",
        "api_key": "test-key",
        "session_id": "session-1",
        "transport": httpx.MockTransport(handler),
        "sleep": lambda _seconds: None,
    }
    options.update(overrides)
    return OpenCodeGoClient(**options)


def ok_response(prompt_tokens: int = 1000, completion_tokens: int = 500) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {"content": '{"subject":"Objet","body":"Corps"}'},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
        },
    )


def messages() -> list[LLMMessage]:
    return [
        LLMMessage(role="system", content="Tu es un assistant."),
        LLMMessage(role="user", content="Rédige une lettre."),
    ]


def test_request_shape_headers_and_cost():
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        captured["payload"] = json.loads(request.content)
        return ok_response()

    client = make_client(handler)
    result = client.complete(
        messages(),
        model="deepseek-v4.1-flash",
        temperature=0.3,
        max_tokens=120,
        json_mode=True,
    )

    request = captured["request"]
    payload = captured["payload"]
    assert isinstance(request, httpx.Request)
    assert isinstance(payload, dict)
    assert str(request.url) == "https://llm.test/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer test-key"
    assert request.headers["x-opencode-session"] == "session-1"
    assert request.headers["user-agent"] == "job-finder/0.1"
    assert payload["model"] == "deepseek-v4.1-flash"
    assert payload["temperature"] == 0.3
    assert payload["max_tokens"] == 120
    assert payload["response_format"] == {"type": "json_object"}

    assert result.prompt_tokens == 1000
    assert result.completion_tokens == 500
    assert result.cost_usd == pytest.approx(0.00045)
    assert result.finish_reason == "stop"


def test_temperature_omitted_when_model_does_not_support_it():
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return ok_response()

    client = make_client(handler)
    client.complete(messages(), model="claude-haiku-5-5", temperature=0.3)

    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert "temperature" not in payload


def test_retries_on_rate_limit():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "0"},
                json={"error": {"message": "rate limited"}},
            )
        return ok_response()

    client = make_client(handler, max_retries=2)
    result = client.complete(messages(), model="deepseek-v4.1-flash")

    assert calls["count"] == 2
    assert result.content


def test_timeout_after_retries():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        raise httpx.ReadTimeout("too slow", request=request)

    client = make_client(handler, max_retries=1)

    with pytest.raises(LLMTimeout):
        client.complete(messages(), model="deepseek-v4.1-flash")

    assert calls["count"] == 2


def test_upstream_error_is_sanitized():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid api key"}})

    client = make_client(handler)

    with pytest.raises(LLMUpstreamError) as error:
        client.complete(messages(), model="deepseek-v4.1-flash")

    assert "401" in str(error.value)
    assert "test-key" not in str(error.value)


def test_json_mode_falls_back_when_rejected():
    payloads: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        payloads.append(payload)
        if len(payloads) == 1:
            return httpx.Response(
                400, json={"error": {"message": "response_format is not supported"}}
            )
        return ok_response()

    client = make_client(handler)
    result = client.complete(messages(), model="deepseek-v4.1-flash", json_mode=True)

    assert "response_format" in payloads[0]
    assert "response_format" not in payloads[1]
    assert result.content


def test_cost_estimation_for_free_model():
    assert estimate_cost_usd("beam-free", 10_000, 5_000) == 0.0
