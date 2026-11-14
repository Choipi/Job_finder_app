"""Catalogue of job sources.

This is the single place that describes where offers can come from. The
frontend renders the campaign checkboxes from it, and each collector will
look itself up by `id`.
"""

from __future__ import annotations

from typing import Any

SOURCES: tuple[dict[str, Any], ...] = (
    {
        "id": "france_travail",
        "label": "France Travail",
        "kind": "api",
        "phase": 4,
        "enabled_by_default": True,
        "note": "API officielle, gratuite, avec lien direct vers l’offre.",
        "warning": None,
    },
    {
        "id": "adzuna",
        "label": "Adzuna",
        "kind": "api",
        "phase": 4,
        "enabled_by_default": True,
        "note": "Agrégateur multi-pays, clé API gratuite.",
        "warning": None,
    },
    {
        "id": "wttj",
        "label": "Welcome to the Jungle",
        "kind": "scrape",
        "phase": 4,
        "enabled_by_default": True,
        "note": "HTML et JSON embarqué, offres tech et startups.",
        "warning": "Scraping : structure susceptible de changer.",
    },
    {
        "id": "hellowork",
        "label": "HelloWork",
        "kind": "scrape",
        "phase": 5,
        "enabled_by_default": False,
        "note": "HTML classique, bon volume généraliste.",
        "warning": "Scraping : structure susceptible de changer.",
    },
    {
        "id": "apec",
        "label": "APEC",
        "kind": "scrape",
        "phase": 5,
        "enabled_by_default": False,
        "note": "Cible les cadres et les experts.",
        "warning": "Scraping : structure susceptible de changer.",
    },
    {
        "id": "indeed",
        "label": "Indeed",
        "kind": "scrape",
        "phase": 5,
        "enabled_by_default": False,
        "note": "Fort volume, rendu JavaScript.",
        "warning": "Anti-bot agressif, contraire aux CGU d’Indeed. À activer en connaissance de cause.",
    },
    {
        "id": "linkedin",
        "label": "LinkedIn",
        "kind": "scrape",
        "phase": 5,
        "enabled_by_default": False,
        "note": "Très fort volume, offres internationales.",
        "warning": "Login et détection : risque de blocage de compte. Désactivé par défaut.",
    },
)

SOURCE_IDS = tuple(source["id"] for source in SOURCES)


def source_by_id(source_id: str) -> dict[str, Any] | None:
    return next((source for source in SOURCES if source["id"] == source_id), None)
