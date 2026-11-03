"""
INFRASTRUCTURE - Dépôt utilisateurs SQLAlchemy
"""
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.models import User
from ..domain.repositories import UserRepositoryInterface
from .models import UserORM


def _to_domain(row: UserORM) -> User:
    return User(
        id=row.id,
        username=row.username,
        display_name=row.display_name,
        role=row.role or "",
        created_at=row.created_at,
        last_seen_at=row.last_seen_at,
    )


class SqlUserRepository(UserRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str) -> Optional[User]:
        row = self.db.get(UserORM, user_id)
        return _to_domain(row) if row else None

    def get_by_username(self, username: str) -> Optional[Tuple[User, str]]:
        row = self.db.scalar(select(UserORM).where(UserORM.username == username))
        return (_to_domain(row), row.password_hash) if row else None

    def create(self, user: User, password_hash: str) -> User:
        row = UserORM(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
            password_hash=password_hash,
            created_at=user.created_at,
        )
        self.db.add(row)
        self.db.commit()
        return _to_domain(row)

    def list_all(self, exclude_id: Optional[str] = None) -> List[User]:
        stmt = select(UserORM).order_by(UserORM.display_name)
        if exclude_id:
            stmt = stmt.where(UserORM.id != exclude_id)
        return [_to_domain(r) for r in self.db.scalars(stmt)]

    def get_many(self, user_ids: List[str]) -> List[User]:
        if not user_ids:
            return []
        rows = self.db.scalars(select(UserORM).where(UserORM.id.in_(user_ids)))
        return [_to_domain(r) for r in rows]

    def touch_last_seen(self, user_id: str, when: datetime) -> None:
        row = self.db.get(UserORM, user_id)
        if row:
            row.last_seen_at = when
            self.db.commit()
