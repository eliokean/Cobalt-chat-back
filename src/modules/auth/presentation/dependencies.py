"""
PRESENTATION - Dépendances Auth (utilisateur courant)
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.exceptions import UnauthorizedException
from src.core.security import decode_access_token

from ..domain.models import User
from ..infrastructure.repositories import SqlUserRepository

_bearer = HTTPBearer(auto_error=False)


def get_user_repository(db: Session = Depends(get_db)) -> SqlUserRepository:
    return SqlUserRepository(db)


def resolve_user_from_token(token: str, repo: SqlUserRepository) -> User:
    user_id = decode_access_token(token)
    user = repo.get_by_id(user_id)
    if not user:
        raise UnauthorizedException("Utilisateur introuvable")
    return user


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    repo: SqlUserRepository = Depends(get_user_repository),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentification requise",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        return resolve_user_from_token(creds.credentials, repo)
    except UnauthorizedException as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, e.message,
                            headers={"WWW-Authenticate": "Bearer"})
