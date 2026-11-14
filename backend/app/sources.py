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
        "enabled_by_default": False,
        "note": "API officielle retirée du catalogue public ; accès sur demande.",
        "warning": "Accès restreint : demande-le via le formulaire de contact France Travail.",
    },
    {
        "id": "adzuna",
        "label": "Adzuna",
        "kind": "api",
        "phase": 4,
        "enabled_by_default": False,
        "note": "Agrégateur multi-pays, clé API gratuite.",
        "warning": "Plan gratuit limité à l’évaluation ; à utiliser en complément.",
    },
    {
        "id": "wttj",
        "label": "Welcome to the Jungle",
        "kind": "scrape",
        "phase": 4,
        "enabled_by_default": False,
        "note": "Sitemap public et pages d’offres, lien de candidature employeur.",
        "warning": "Pages protégées après quelques requêtes ; collecte lente et tolérante requise.",
    },
    {
        "id": "hellowork",
        "label": "HelloWork",
        "kind": "scrape",
        "phase": 5,
        "enabled_by_default": False,
        "note": "HTML classique, bon volume généraliste.",
        "warning": "Cloudflare bloque les requêtes automatisées (403). Non exploitable en l’état.",
    },
    {
        "id": "apec",
        "label": "APEC",
        "kind": "scrape",
        "phase": 5,
        "enabled_by_default": False,
        "note": "Cible les cadres et les experts.",
        "warning": "DataDome bloque les requêtes automatisées. Non exploitable en l’état.",
    },
    {
        "id": "indeed",
        "label": "Indeed",
        "kind": "scrape",
        "phase": 5,
        "enabled_by_default": False,
        "note": "Fort volume, rendu JavaScript.",
        "warning": "403 et anti-bot agressif ; contraire aux CGU d’Indeed.",
    },
    {
        "id": "linkedin",
        "label": "LinkedIn",
        "kind": "scrape",
        "phase": 5,
        "enabled_by_default": False,
        "note": "Très fort volume, offres internationales.",
        "warning": "Automatisation interdite par les CGU de LinkedIn. À exclure.",
    },
)

SOURCE_IDS = tuple(source["id"] for source in SOURCES)


def source_by_id(source_id: str) -> dict[str, Any] | None:
    return next((source for source in SOURCES if source["id"] == source_id), None)
