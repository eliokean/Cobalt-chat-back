"""
PRESENTATION - Injection de Dépendances (FastAPI Depends)
Assure le câblage entre l'infrastructure et la couche application.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.realtime import manager
from src.modules.auth.presentation.dependencies import get_user_repository
from src.modules.auth.infrastructure.repositories import SqlUserRepository
from src.modules.crypt.application.use_cases import MessageCryptoService
from src.modules.crypt.presentation.dependencies import get_crypto_service

from ..application.use_cases import ChatContext
from ..infrastructure.repositories import SqlChatRepository


def get_chat_context(
    db: Session = Depends(get_db),
    users: SqlUserRepository = Depends(get_user_repository),
    crypto: MessageCryptoService = Depends(get_crypto_service),
) -> ChatContext:
    return ChatContext(SqlChatRepository(db), users, crypto, manager.is_online)
