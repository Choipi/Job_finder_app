"""Deterministic LLM client for tests and offline development.

Enable with `LLM_PROVIDER=mock` in `.env`. It returns plausible JSON so the
whole pipeline (prompt building, parsing, persistence, UI) can be exercised
without a key or a network call.
"""

from __future__ import annotations

import json
import re
from typing import Sequence

from .client import LLMMessage, LLMResult


class MockLLMClient:
    def complete(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResult:
        prompt = "\n".join(message.content for message in messages)
        prompt_tokens = max(len(prompt) // 4, 1)

        if json_mode:
            title = _tag(prompt, "poste") or "le poste"
            company = _tag(prompt, "entreprise") or "votre entreprise"
            content = json.dumps(
                {
                    "subject": f"Candidature — {title}",
                    "body": (
                        "Madame, Monsieur,\n\n"
                        f"Je vous adresse ma candidature pour le poste de {title} "
                        f"au sein de {company}.\n\n"
                        "Mon parcours et mes compétences correspondent aux besoins décrits "
                        "dans votre annonce. J’apprécie particulièrement la clarté de votre "
                        "approche et je serais heureux de contribuer à vos prochains projets.\n\n"
                        "Je reste à votre disposition pour en échanger.\n\n"
                        "Bien cordialement,\n\n"
                        "[Mode démo : cette lettre est générée localement, sans appel réseau.]"
                    ),
                },
                ensure_ascii=False,
            )
        else:
            content = "OK (mode démo)"

        completion_tokens = max(len(content) // 4, 1)
        return LLMResult(
            content=content,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=0.0,
            duration_ms=0,
            finish_reason="stop",
        )


def _tag(prompt: str, name: str) -> str | None:
    match = re.search(rf"<{name}>(.*?)</{name}>", prompt, re.DOTALL)
    if not match:
        return None
    value = " ".join(match.group(1).split())
    return value[:120] or None
