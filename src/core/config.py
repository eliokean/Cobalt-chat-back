"""
CORE - Configuration globale & variables d'environnement
Utilise Pydantic Settings pour charger la configuration (.env ou variables d'environnement).
"""
import json
from typing import Annotated, List

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Cobalt Chat API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Origines CORS : JSON ('["https://a","https://b"]') ou liste séparée par des virgules
    ALLOWED_ORIGINS: Annotated[List[str], NoDecode] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Base de données : SQLite par défaut, PostgreSQL en production
    # (ex. postgresql://user:pass@host:5432/db — l'URL Render est acceptée telle quelle)
    DATABASE_URL: str = "sqlite:///./cobalt_chat.db"

    # Authentification JWT — À CHANGER via l'environnement en dehors du développement
    JWT_SECRET: str = "dev-secret-change-me-please-32-bytes-min"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7

    # Taille des modules RSA générés pour chaque discussion
    RSA_KEY_BITS: int = 1024

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_origins(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                value = json.loads(value)
            else:
                value = [v for v in value.split(",")]
        return [o.strip().rstrip("/") for o in value if o and o.strip()]

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def _normalize_db_url(cls, value: str) -> str:
        # Render/Heroku fournissent postgres:// ou postgresql:// ; SQLAlchemy + psycopg 3
        # attendent postgresql+psycopg://
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix):]
        return value


settings = Settings()
