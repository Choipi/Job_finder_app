"""OpenAI-compatible client for OpenCode Go.

Request shape:

    POST {base_url}/chat/completions
    Authorization: Bearer <key>
    x-opencode-session: <stable id>
    User-Agent: job-finder/0.1

Reliability choices worth studying:

- timeouts are explicit, so a stuck request cannot hang a Flask worker;
- 429/5xx and network errors are retried with exponential backoff + jitter;
- `Retry-After` is honoured when the provider sends it;
- JSON mode is attempted, then disabled once if the provider rejects
  `response_format` (graceful degradation instead of a hard failure).
"""

from __future__ import annotations

import json
import logging
import random
import time
from typing import Any, Callable, Sequence

import httpx

from .catalog import estimate_cost_usd, get_model
from .client import LLMMessage, LLMResult
from .errors import LLMTimeout, LLMUpstreamError

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}
MAX_RETRY_AFTER_SECONDS = 30.0


class OpenCodeGoClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        session_id: str = "job-finder-local",
        user_agent: str = "job-finder/0.1",
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self.session_id = session_id
        self.user_agent = user_agent
        self._transport = transport
        self._sleep = sleep

    # -- public API -------------------------------------------------------
    def complete(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResult:
        info = get_model(model)
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        # Some models (Claude Haiku, Kimi, Gemini here) reject temperature.
        if temperature is not None and (info is None or info.supports_temperature):
            payload["temperature"] = temperature
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        started = time.perf_counter()
        attempt = 0
        json_mode_active = json_mode

        while True:
            try:
                response = self._post(payload)
            except httpx.TimeoutException as error:
                if attempt < self.max_retries:
                    self._sleep(self._backoff(attempt))
                    attempt += 1
                    continue
                raise LLMTimeout(
                    "Le modèle n’a pas répondu dans le délai imparti. Réessaie ou augmente LLM_TIMEOUT_SECONDS."
                ) from error
            except httpx.HTTPError as error:
                if attempt < self.max_retries:
                    self._sleep(self._backoff(attempt))
                    attempt += 1
                    continue
                raise LLMUpstreamError(
                    f"Connexion au fournisseur impossible ({type(error).__name__})."
                ) from error

            body_text = response.text

            # Graceful fallback: some models do not support native JSON mode.
            if (
                response.status_code == 400
                and json_mode_active
                and "response_format" in body_text.lower()
            ):
                logger.info("Model %s rejected response_format, retrying without JSON mode", model)
                payload.pop("response_format", None)
                json_mode_active = False
                continue

            if response.status_code in RETRYABLE_STATUS and attempt < self.max_retries:
                delay = self._retry_delay(attempt, response.headers.get("Retry-After"))
                logger.warning(
                    "LLM HTTP %s, retry %s/%s in %.2fs",
                    response.status_code,
                    attempt + 1,
                    self.max_retries,
                    delay,
                )
                self._sleep(delay)
                attempt += 1
                continue

            if response.status_code >= 400:
                raise LLMUpstreamError(
                    self._error_message(response),
                    upstream_status=response.status_code,
                )

            data = self._parse_json(response)
            duration_ms = int((time.perf_counter() - started) * 1000)

            try:
                choice = data["choices"][0]
                content = choice["message"]["content"]
            except (KeyError, IndexError, TypeError) as error:
                raise LLMUpstreamError("Réponse inattendue du fournisseur.") from error

            if not isinstance(content, str) or not content.strip():
                finish_reason = choice.get("finish_reason")
                raise LLMUpstreamError(
                    "Le modèle a renvoyé une réponse vide "
                    f"(finish_reason={finish_reason or 'inconnu'}). "
                    "Les modèles de raisonnement ont besoin d’un budget de tokens plus large."
                )

            usage = data.get("usage") or {}
            prompt_tokens = _as_int(usage.get("prompt_tokens"))
            completion_tokens = _as_int(usage.get("completion_tokens"))
            cost = estimate_cost_usd(model, prompt_tokens, completion_tokens)
            finish_reason = choice.get("finish_reason")

            logger.info(
                "LLM ok model=%s tokens=%s+%s cost=%.6f duration=%sms",
                model,
                prompt_tokens,
                completion_tokens,
                cost,
                duration_ms,
            )

            return LLMResult(
                content=content,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost,
                duration_ms=duration_ms,
                finish_reason=finish_reason if isinstance(finish_reason, str) else None,
            )

    # -- internals --------------------------------------------------------
    def _post(self, payload: dict[str, Any]) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self.user_agent,
            "x-opencode-session": self.session_id,
        }
        with httpx.Client(
            timeout=httpx.Timeout(self.timeout_seconds),
            transport=self._transport,
        ) as client:
            return client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

    def _backoff(self, attempt: int) -> float:
        # 1s, 2s, 4s… with jitter to avoid synchronised retries.
        return (2**attempt) + random.uniform(0, 0.5)

    def _retry_delay(self, attempt: int, retry_after: str | None) -> float:
        if retry_after:
            try:
                return min(float(retry_after), MAX_RETRY_AFTER_SECONDS)
            except ValueError:
                pass
        return self._backoff(attempt)

    def _parse_json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as error:
            raise LLMUpstreamError("Le fournisseur n’a pas renvoyé du JSON.") from error
        if not isinstance(data, dict):
            raise LLMUpstreamError("Le fournisseur n’a pas renvoyé un objet JSON.")
        return data

    def _error_message(self, response: httpx.Response) -> str:
        """Extract a short message, never echo the key or the full payload."""
        try:
            data = response.json()
            message = (data.get("error") or {}).get("message")
            if isinstance(message, str) and message.strip():
                return f"Erreur du fournisseur ({response.status_code}) : {message[:300]}"
        except ValueError:
            pass
        return f"Erreur du fournisseur (HTTP {response.status_code})."


def _as_int(value: object) -> int:
    try:
        return max(int(value), 0)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
