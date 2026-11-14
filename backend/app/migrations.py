"""Tiny SQLite migrations for columns added after the first release.

The project deliberately avoids Alembic for now: one small, explicit ALTER is
easier to understand than a migration framework for a local application. New
tables are handled by `db.create_all()`; only new columns need this.
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from .extensions import db


def apply_sqlite_migrations() -> None:
    if db.engine.dialect.name != "sqlite":
        return

    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())

    if "generated_letter" in tables:
        columns = {column["name"] for column in inspector.get_columns("generated_letter")}
        if "offer_id" not in columns:
            with db.engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE generated_letter ADD COLUMN offer_id INTEGER")
                )
