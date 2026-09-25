"""
Central configuration, loaded once from the environment.

Everything degrades gracefully when optional keys are missing so the app
runs out of the box for a demo.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings:
    """Runtime settings resolved from environment variables."""

    # --- Core -------------------------------------------------------------
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-insecure-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_ttl_hours: int = int(os.getenv("JWT_TTL_HOURS", str(24 * 7)))

    database_url: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'onepick.db'}"
    )

    # Comma-separated list of admin emails.
    admin_emails: set[str] = {
        e.strip().lower()
        for e in os.getenv("ADMIN_EMAILS", "demo@onepick.app").split(",")
        if e.strip()
    }

    # --- Recommendations --------------------------------------------------
    daily_reroll_limit: int = int(os.getenv("DAILY_REROLL_LIMIT", "3"))
    place_promotion_votes: int = int(os.getenv("PLACE_PROMOTION_VOTES", "3"))

    # --- AI (optional) ----------------------------------------------------
    use_anthropic: bool = os.getenv("USE_ANTHROPIC", "false").lower() == "true"
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

    # --- CORS -------------------------------------------------------------
    cors_origins: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "*").split(",")
        if o.strip()
    ]

    def is_admin(self, email: str | None) -> bool:
        return (email or "").lower() in self.admin_emails


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
