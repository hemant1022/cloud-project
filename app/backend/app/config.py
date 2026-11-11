"""Application settings loaded from environment variables."""

from __future__ import annotations

import logging

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://inventory:inventory@db:5432/inventory"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    admin_email: str = "admin@inventory.local"
    admin_password: str = "change-me-admin"

    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    log_stack: str = "backend"
    log_level: str = "INFO"

    import_max_rows: int = 10_000
    import_max_bytes: int = 5 * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def log_level_int(self) -> int:
        return getattr(logging, self.log_level.upper(), logging.INFO)


settings = Settings()
