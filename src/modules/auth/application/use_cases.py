"""
APPLICATION - Cas d'utilisation Auth
"""
import uuid
from datetime import datetime, timezone
from typing import Callable, List

from src.core.security import create_access_token, hash_password, verify_password

from ..domain.exceptions import InvalidCredentialsError, UsernameTakenError
from ..domain.models import User
from ..domain.repositories import UserRepositoryInterface
from .dto import LoginInputDTO, RegisterInputDTO, TokenOutputDTO, UserOutputDTO


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RegisterUseCase:
    def __init__(self, repo: UserRepositoryInterface):
        self.repo = repo

    def execute(self, dto: RegisterInputDTO) -> TokenOutputDTO:
        username = User.normalize_username(dto.username)
        User.validate_username(username)
        User.validate_password(dto.password)
        if self.repo.get_by_username(username):
            raise UsernameTakenError("Ce nom d'utilisateur est déjà pris.")

        user = User(
            id=str(uuid.uuid4()),
            username=username,
            display_name=dto.display_name.strip(),
            role=dto.role.strip(),
            created_at=utcnow(),
        )
        user = self.repo.create(user, hash_password(dto.password))
        return TokenOutputDTO(
            access_token=create_access_token(user.id),
            user=UserOutputDTO.from_domain(user),
        )


class LoginUseCase:
    def __init__(self, repo: UserRepositoryInterface):
        self.repo = repo

    def execute(self, dto: LoginInputDTO) -> TokenOutputDTO:
        found = self.repo.get_by_username(User.normalize_username(dto.username))
        if not found or not verify_password(dto.password, found[1]):
            raise InvalidCredentialsError("Identifiants incorrects.")
        user = found[0]
        return TokenOutputDTO(
            access_token=create_access_token(user.id),
            user=UserOutputDTO.from_domain(user),
        )


class ListContactsUseCase:
    def __init__(self, repo: UserRepositoryInterface, is_online: Callable[[str], bool]):
        self.repo = repo
        self.is_online = is_online

    def execute(self, current_user_id: str) -> List[UserOutputDTO]:
        return [
            UserOutputDTO.from_domain(u, self.is_online(u.id))
            for u in self.repo.list_all(exclude_id=current_user_id)
        ]
