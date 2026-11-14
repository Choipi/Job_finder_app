"""Small validation helpers for JSON payloads.

The goal is readability: routes describe *what* a field is, this module takes
care of cleaning and collecting errors. All errors are gathered and raised at
once by `Validator.finish()`, so the user sees every problem in one save.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Iterable

from flask import request

from .errors import ValidationError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def request_payload() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValidationError("Un corps JSON est attendu.")
    return payload


class Validator:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.errors: dict[str, str] = {}

    # -- helpers ---------------------------------------------------------
    def add_error(self, field: str, message: str) -> None:
        self.errors.setdefault(field, message)

    def finish(self) -> None:
        """Raise a single ValidationError containing every field error."""
        if self.errors:
            raise ValidationError("Certains champs sont invalides.", dict(self.errors))

    # -- field readers ---------------------------------------------------
    def text(
        self,
        key: str,
        label: str,
        *,
        max_length: int = 255,
        required: bool = False,
    ) -> str:
        raw = self.data.get(key, "")
        if raw is None:
            raw = ""
        if not isinstance(raw, str):
            self.add_error(key, f"{label} doit être du texte.")
            return ""
        value = raw.strip()
        if required and not value:
            self.add_error(key, f"{label} est obligatoire.")
        elif len(value) > max_length:
            self.add_error(key, f"{label} ne doit pas dépasser {max_length} caractères.")
            value = value[:max_length]
        return value

    def email(self, key: str, label: str) -> str:
        value = self.text(key, label, max_length=180)
        if value and not EMAIL_RE.match(value):
            self.add_error(key, f"{label} n’est pas une adresse valide.")
        return value

    def integer(
        self,
        key: str,
        label: str,
        *,
        minimum: int,
        maximum: int,
        default: int,
    ) -> int:
        raw = self.data.get(key, default)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            self.add_error(key, f"{label} doit être un nombre entier.")
            return default

        if not minimum <= value <= maximum:
            self.add_error(key, f"{label} doit être compris entre {minimum} et {maximum}.")
        return value

    def choice(self, key: str, label: str, choices: Iterable[str], *, default: str) -> str:
        allowed = tuple(choices)
        raw = self.data.get(key, default)
        if raw not in allowed:
            self.add_error(key, f"{label} doit être l’une des valeurs : {', '.join(allowed)}.")
            return default
        return str(raw)

    def boolean(self, key: str, default: bool = False) -> bool:
        raw = self.data.get(key, default)
        if isinstance(raw, bool):
            return raw
        self.add_error(key, "Valeur booléenne attendue.")
        return default

    def string_list(
        self,
        key: str,
        label: str,
        *,
        allowed: Iterable[str] | None = None,
        max_items: int = 20,
        max_length: int = 80,
        required: bool = False,
    ) -> list[str]:
        raw = self.data.get(key, [])
        if raw is None:
            raw = []
        if not isinstance(raw, list):
            self.add_error(key, f"{label} doit être une liste.")
            return []

        cleaned: list[str] = []
        for item in raw:
            if not isinstance(item, str):
                self.add_error(key, f"{label} ne doit contenir que du texte.")
                continue
            value = item.strip()
            if not value:
                continue
            if len(value) > max_length:
                self.add_error(key, f"Chaque valeur de « {label} » est limitée à {max_length} caractères.")
                continue
            if value not in cleaned:
                cleaned.append(value)

        if len(cleaned) > max_items:
            self.add_error(key, f"« {label} » est limité à {max_items} valeurs.")
            cleaned = cleaned[:max_items]

        if allowed is not None:
            allowed_values = tuple(allowed)
            invalid = [value for value in cleaned if value not in allowed_values]
            if invalid:
                self.add_error(key, f"Valeur inconnue pour « {label} » : {', '.join(invalid)}.")

        if required and not cleaned:
            self.add_error(key, f"« {label} » doit contenir au moins une valeur.")

        return cleaned

    def date(self, key: str, label: str, *, required: bool = True) -> date | None:
        raw = self.data.get(key)
        if not raw:
            if required:
                self.add_error(key, f"{label} est obligatoire.")
            return None
        try:
            return date.fromisoformat(str(raw))
        except ValueError:
            self.add_error(key, f"{label} doit être au format AAAA-MM-JJ.")
            return None
