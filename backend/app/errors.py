"""Application-level exceptions and their HTTP representation."""

from __future__ import annotations

from typing import Any


class ValidationError(Exception):
    """Invalid user input.

    `fields` maps a form field name to a human-readable message so the Vue
    forms can display errors next to the right input.
    """

    def __init__(self, message: str, fields: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.fields: dict[str, str] = fields or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": 400,
                "name": "Validation Error",
                "message": self.message,
                "fields": self.fields,
            }
        }
