"""Flask CLI commands for the employer watchlist.

Examples:
    flask employers-seed
    flask employers-discover --limit 10
    flask employers-collect --limit 5 --max-offers 50
"""

from __future__ import annotations

import json

import click
from flask import Flask
from flask.cli import with_appcontext

from .employers.detection import discover_pending
from .employers.service import collect_ready, employer_stats, seed_employers


@click.command("employers-seed")
@with_appcontext
def seed_command() -> None:
    """Load the AI France watchlist (200 employers)."""
    summary = seed_employers()
    click.echo(json.dumps({"seed": summary, "stats": employer_stats()}, ensure_ascii=False))


@click.command("employers-discover")
@click.option("--limit", default=10, type=int, help="Nombre d'employeurs à analyser.")
@with_appcontext
def discover_command(limit: int) -> None:
    """Detect the ATS of pending employers."""
    summary = discover_pending(limit=max(1, min(limit, 50)))
    click.echo(json.dumps(summary, ensure_ascii=False, indent=2))


@click.command("employers-collect")
@click.option("--limit", default=5, type=int, help="Nombre d'employeurs à interroger.")
@click.option("--max-offers", default=50, type=int, help="Offres maximum par employeur.")
@with_appcontext
def collect_command(limit: int, max_offers: int) -> None:
    """Fetch offers from employers whose ATS is known."""
    summary = collect_ready(limit=max(1, min(limit, 50)), max_offers=max(1, min(max_offers, 200)))
    click.echo(json.dumps(summary, ensure_ascii=False, indent=2))


def register_cli(app: Flask) -> None:
    app.cli.add_command(seed_command)
    app.cli.add_command(discover_command)
    app.cli.add_command(collect_command)
