"""Application configuration.

Everything that comes from the environment is read here, once, in a single
place. The rest of the code receives a `Settings` instance instead of reading
`os.environ` directly: it keeps the configuration testable and makes the
security surface easy to audit (the API key never leaves this module except
through `Settings`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

# Load the root `.env` file. Real environment variables always win.
load_dotenv(REPO_ROOT / ".env")


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_list(value: str | None, default: tuple[str, ...] = ()) -> list[str]:
    if not value:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings.

    Every field has a default so tests can build a custom instance:
        Settings(opencode_api_key="test", opencode_base_url="http://llm.test/v1")
    """

    app_name: str = "Job Finder API"
    version: str = "0.1.0"
    debug: bool = field(default_factory=lambda: _as_bool(os.getenv("FLASK_DEBUG"), False))
    host: str = field(default_factory=lambda: os.getenv("HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "5000")))

    cors_origins: list[str] = field(
        default_factory=lambda: _as_list(
            os.getenv("CORS_ORIGINS"),
            ("http://localhost:5173", "http://127.0.0.1:5173"),
        )
    )

    # OpenCode Go, reached through an OpenAI-compatible endpoint.
    opencode_base_url: str = field(
        default_factory=lambda: (
            os.getenv("OPENCODE_BASE_URL")
            or "https://opencode.ai/inference/go/openai/v1"
        ).rstrip("/")
    )
    opencode_api_key: str = field(default_factory=lambda: os.getenv("OPENCODE_API_KEY", ""))
    scoring_model: str = field(default_factory=lambda: os.getenv("SCORING_MODEL", "deepseek-v4.1-flash"))
    letter_model: str = field(default_factory=lambda: os.getenv("LETTER_MODEL", "claude-haiku-5-5"))

    # --- LLM runtime -------------------------------------------------------
    # "opencode_go" for real calls, "mock" to develop without a key.
    llm_provider: str = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "opencode_go").strip().lower()
    )
    llm_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
    )
    llm_max_retries: int = field(
        default_factory=lambda: int(os.getenv("LLM_MAX_RETRIES", "2"))
    )
    llm_temperature_letter: float = field(
        default_factory=lambda: float(os.getenv("LLM_TEMPERATURE_LETTER", "0.3"))
    )
    llm_session_id: str = field(
        default_factory=lambda: os.getenv("LLM_SESSION_ID", "job-finder-local")
    )

    max_upload_mb: int = field(default_factory=lambda: int(os.getenv("MAX_UPLOAD_MB", "10")))
    max_scoring_per_scan: int = field(default_factory=lambda: int(os.getenv("MAX_SCORING_PER_SCAN", "150")))

    # --- Scheduler ---------------------------------------------------------
    scheduler_enabled: bool = field(
        default_factory=lambda: _as_bool(os.getenv("SCHEDULER_ENABLED"), False)
    )
    scheduler_interval_seconds: int = field(
        default_factory=lambda: int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "60"))
    )
    scan_collect_employers: int = field(
        default_factory=lambda: int(os.getenv("SCAN_COLLECT_EMPLOYERS", "5"))
    )
    scan_score_offers: int = field(
        default_factory=lambda: int(os.getenv("SCAN_SCORE_OFFERS", "20"))
    )

    # --- Persistence -------------------------------------------------------
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL")
        or f"sqlite:///{BACKEND_DIR / 'instance' / 'job_finder.db'}"
    )
    upload_dir: Path = field(
        default_factory=lambda: Path(os.getenv("UPLOAD_DIR") or BACKEND_DIR / "uploads")
    )

    @property
    def llm_configured(self) -> bool:
        return bool(self.opencode_base_url and self.opencode_api_key)

    @property
    def llm_ready(self) -> bool:
        """True when a call can be attempted: real key present or mock mode."""
        return self.llm_provider == "mock" or self.llm_configured

    @property
    def public_llm_config(self) -> dict[str, object]:
        """LLM information safe to send to the browser.

        The API key is deliberately absent: the frontend only needs to know
        whether the backend is ready to call the model.
        """
        return {
            "configured": self.llm_configured,
            "ready": self.llm_ready,
            "base_url_configured": bool(self.opencode_base_url),
            "provider": self.llm_provider,
            "mock": self.llm_provider == "mock",
            "scoring_model": self.scoring_model,
            "letter_model": self.letter_model,
        }
