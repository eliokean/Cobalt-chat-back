"""
PRESENTATION - Routes Auth
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.realtime import manager

from ..application.dto import LoginInputDTO, RegisterInputDTO, TokenOutputDTO, UserOutputDTO
from ..application.use_cases import ListContactsUseCase, LoginUseCase, RegisterUseCase
from ..domain.exceptions import (
    InvalidCredentialsError,
    InvalidUsernameError,
    UsernameTakenError,
    WeakPasswordError,
)
from ..domain.models import User
from ..infrastructure.repositories import SqlUserRepository
from .dependencies import get_current_user, get_user_repository

router = APIRouter(tags=["Auth"])


@router.post("/auth/register", response_model=TokenOutputDTO, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterInputDTO, repo: SqlUserRepository = Depends(get_user_repository)):
    try:
        result = RegisterUseCase(repo).execute(payload)
    except (InvalidUsernameError, WeakPasswordError) as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except UsernameTakenError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    # Les autres utilisateurs connectés voient apparaître le nouveau contact
    manager.notify(manager.online_users(), {"type": "user.new", "user": result.user.model_dump()})
    return result


@router.post("/auth/login", response_model=TokenOutputDTO)
def login(payload: LoginInputDTO, repo: SqlUserRepository = Depends(get_user_repository)):
    try:
        return LoginUseCase(repo).execute(payload)
    except InvalidCredentialsError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))


@router.get("/auth/me", response_model=UserOutputDTO)
def me(user: User = Depends(get_current_user)):
    return UserOutputDTO.from_domain(user, is_online=True)


@router.get("/users", response_model=List[UserOutputDTO])
def list_users(
    user: User = Depends(get_current_user),
    repo: SqlUserRepository = Depends(get_user_repository),
):
    return ListContactsUseCase(repo, manager.is_online).execute(user.id)
