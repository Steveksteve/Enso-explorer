"""Configuration lue dans les variables d'environnement (aucun secret dans le code)."""

import os
from dataclasses import dataclass, field


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL", "postgresql+psycopg://enso:enso_dev@localhost:5432/enso"
        )
    )
    cors_origins: list[str] = field(
        default_factory=lambda: _split(os.environ.get("CORS_ORIGINS", "http://localhost:5173"))
    )
    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))


settings = Settings()
