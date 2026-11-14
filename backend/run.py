"""Development entry point.

    cd backend
    python run.py

Or with the Flask CLI:
    flask --app run:app run
"""

from __future__ import annotations

from app import create_app
from app.config import Settings

settings = Settings()
app = create_app(settings)


if __name__ == "__main__":
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
