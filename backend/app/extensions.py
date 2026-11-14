"""Shared Flask extensions.

Kept in their own module so models and blueprints can import `db` without
creating a circular import through the application factory.
"""

from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
