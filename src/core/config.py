"""
CORE - Configuration globale & variables d'environnement
Utilise Pydantic Settings pour charger la configuration (.env).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Cobalt Chat API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Base de données (SQLite par défaut : fichier local)
    DATABASE_URL: str = "sqlite:///./cobalt_chat.db"

    # Authentification JWT — À CHANGER via .env en dehors du développement
    JWT_SECRET: str = "dev-secret-change-me-please-32-bytes-min"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7

    # Taille des modules RSA générés pour chaque discussion
    RSA_KEY_BITS: int = 1024

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
