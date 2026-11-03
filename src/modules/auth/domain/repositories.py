"""
DOMAINE - Port du dépôt utilisateurs.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple

from .models import User


class UserRepositoryInterface(ABC):
    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]: ...

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[Tuple[User, str]]:
        """Retourne (utilisateur, hash du mot de passe)."""

    @abstractmethod
    def create(self, user: User, password_hash: str) -> User: ...

    @abstractmethod
    def list_all(self, exclude_id: Optional[str] = None) -> List[User]: ...

    @abstractmethod
    def get_many(self, user_ids: List[str]) -> List[User]: ...

    @abstractmethod
    def touch_last_seen(self, user_id: str, when: datetime) -> None: ...
