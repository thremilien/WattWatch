"""Application settings, loaded from environment variables and `.env`."""

import secrets
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """WattWatch runtime configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    admin_username: str = "admin"
    admin_password: str = ""

    secret_key: str = secrets.token_urlsafe(32)

    kasa_host: str = "192.168.10.8"

    poll_interval_seconds: int = 5
    history_interval_seconds: int = 60
    history_retention_days: int = 90

    database_path: Path = Path("./data/wattwatch.db")

    session_lifetime_hours: int = 720

    frontend_dist: Path = REPO_ROOT / "frontend" / "dist"

    @field_validator("admin_password")
    @classmethod
    def _require_admin_password(cls, value: str) -> str:
        if not value:
            raise ValueError(
                "ADMIN_PASSWORD must be set (non-empty) — refusing to start with no admin "
                "password configured."
            )
        return value


settings = Settings()
