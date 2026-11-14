"""Letter generation: prompt assembly, LLM call, parsing and persistence.

The whole orchestration lives here so the HTTP route stays thin:

    validate payload -> build messages -> call client -> parse JSON
    -> save letter + usage -> return

Every step is explicit. This is the file to read to understand how a business
feature uses an LLM.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

from ..config import Settings
from ..extensions import db
from ..llm import LLMClient, LLMError, LLMMessage
from ..llm.telemetry import record_llm_call
from ..models import GeneratedLetter, Profile

logger = logging.getLogger(__name__)

PROMPT_VERSION = "letter/v1"
PROMPT_PATH = Path(__file__).parent / "prompts" / "letter_system.md"

MAX_OUTPUT_TOKENS = 4_000
TASK = "letter"

# Context stays bounded: a 40-page CV or a giant job ad must not silently
# blow up the context window or the bill.
LIMITS = {
    "summary": 3_000,
    "cv": 20_000,
    "template": 8_000,
    "description": 12_000,
    "instructions": 1_000,
}


@dataclass(frozen=True)
class LetterInput:
    job_title: str
    company: str
    job_description: str
    source_url: str = ""
    instructions: str = ""


@dataclass(frozen=True)
class LetterOutcome:
    letter: GeneratedLetter
    truncated_fields: list[str]


def generate_letter(
    *,
    letter_input: LetterInput,
    profile: Profile,
    model: str,
    client: LLMClient,
    settings: Settings,
) -> LetterOutcome:
    messages, truncated_fields = build_messages(letter_input, profile)
    started = time.perf_counter()

    try:
        result = client.complete(
            messages,
            model=model,
            temperature=settings.llm_temperature_letter,
            max_tokens=MAX_OUTPUT_TOKENS,
            json_mode=True,
        )
    except LLMError as error:
        duration_ms = int((time.perf_counter() - started) * 1000)
        record_llm_call(
            task=TASK,
            model=model,
            prompt_version=PROMPT_VERSION,
            status="error",
            duration_ms=duration_ms,
            error=error.message,
        )
        db.session.commit()
        raise

    subject, body = parse_letter(result.content, fallback_subject=_fallback_subject(letter_input))

    letter = GeneratedLetter(
        job_title=letter_input.job_title,
        company=letter_input.company,
        source_url=letter_input.source_url,
        job_description=letter_input.job_description,
        instructions=letter_input.instructions,
        subject=subject,
        body=body,
        model=result.model,
        prompt_version=PROMPT_VERSION,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cost_usd=result.cost_usd,
        duration_ms=result.duration_ms,
    )
    db.session.add(letter)
    record_llm_call(
        task=TASK,
        model=result.model,
        prompt_version=PROMPT_VERSION,
        status="ok",
        duration_ms=result.duration_ms,
        result=result,
    )
    db.session.commit()

    return LetterOutcome(letter=letter, truncated_fields=truncated_fields)


def build_messages(
    letter_input: LetterInput, profile: Profile
) -> tuple[list[LLMMessage], list[str]]:
    """Assemble the two prompt layers and report truncated context fields."""
    truncated: list[str] = []

    summary, was_truncated = _truncate(profile.summary.strip(), LIMITS["summary"])
    truncated += ["summary"] if was_truncated else []

    cv, was_truncated = _truncate(profile.cv_text.strip(), LIMITS["cv"])
    truncated += ["cv"] if was_truncated else []

    template, was_truncated = _truncate(
        profile.letter_template.strip(), LIMITS["template"]
    )
    truncated += ["template"] if was_truncated else []

    description, was_truncated = _truncate(
        letter_input.job_description.strip(), LIMITS["description"]
    )
    truncated += ["description"] if was_truncated else []

    instructions, was_truncated = _truncate(
        letter_input.instructions.strip(), LIMITS["instructions"]
    )
    truncated += ["instructions"] if was_truncated else []

    identity = " ".join(
        part
        for part in [
            f"{profile.first_name} {profile.last_name}".strip(),
            profile.headline.strip(),
            profile.city.strip(),
        ]
        if part
    )

    user_message = "\n".join(
        [
            "<profil>",
            identity or "Non renseigné",
            summary or "Non renseigné",
            "</profil>",
            "",
            "<cv>",
            cv or "Non renseigné",
            "</cv>",
            "",
            "<lettre_type>",
            template or "Non renseignée",
            "</lettre_type>",
            "",
            "<offre>",
            f"<poste>{letter_input.job_title.strip()}</poste>",
            f"<entreprise>{letter_input.company.strip()}</entreprise>",
            f"<url>{letter_input.source_url.strip() or 'Non renseignée'}</url>",
            "<description>",
            description,
            "</description>",
            "</offre>",
            "",
            "<consigne_supplementaire>",
            instructions or "Aucune.",
            "</consigne_supplementaire>",
            "",
            "Rédige la lettre au format JSON demandé.",
        ]
    )

    return [
        LLMMessage(role="system", content=PROMPT_PATH.read_text(encoding="utf-8")),
        LLMMessage(role="user", content=user_message),
    ], truncated


def parse_letter(raw: str, *, fallback_subject: str) -> tuple[str, str]:
    """Parse the model output, tolerating fenced or malformed JSON.

    Falling back to the raw text keeps the feature usable with models that do
    not follow the format. The event is logged so the prompt can be improved.
    """
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    candidates = [text]
    first_brace, last_brace = text.find("{"), text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidates.append(text[first_brace : last_brace + 1])

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        subject = str(data.get("subject") or fallback_subject).strip()
        body = str(data.get("body") or "").strip()
        if body:
            return subject[:300], body

    logger.warning("Letter JSON parsing failed, using raw output")
    body = raw.strip()
    if not body:
        raise ValueError("Le modèle n’a renvoyé aucun texte exploitable.")
    return fallback_subject[:300], body


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit].rstrip() + "\n[…contenu tronqué…]", True


def _fallback_subject(letter_input: LetterInput) -> str:
    if letter_input.company:
        return f"Candidature — {letter_input.job_title} ({letter_input.company})"[:300]
    return f"Candidature — {letter_input.job_title}"[:300]


# Re-exported for tests and for the future scoring service.
__all__ = [
    "LIMITS",
    "PROMPT_VERSION",
    "LetterInput",
    "LetterOutcome",
    "build_messages",
    "generate_letter",
    "parse_letter",
]
