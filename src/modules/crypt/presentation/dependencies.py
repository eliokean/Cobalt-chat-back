"""
PRESENTATION - Dépendances Crypt
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import get_db

from ..application.use_cases import MessageCryptoService
from ..infrastructure.repositories import SqlKeyRepository


def get_crypto_service(db: Session = Depends(get_db)) -> MessageCryptoService:
    return MessageCryptoService(SqlKeyRepository(db), settings.RSA_KEY_BITS)
