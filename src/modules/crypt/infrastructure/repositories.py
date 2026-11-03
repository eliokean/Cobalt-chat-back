"""
INFRASTRUCTURE - Dépôt SQLAlchemy des clés RSA
"""
from typing import Optional

from sqlalchemy.orm import Session

from ..domain.models import RsaKeyPair
from ..domain.repositories import KeyRepositoryInterface
from .models import RsaKeyORM


class SqlKeyRepository(KeyRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    def get(self, owner_id: str) -> Optional[RsaKeyPair]:
        row = self.db.get(RsaKeyORM, owner_id)
        if not row:
            return None
        return RsaKeyPair(
            owner_id=row.owner_id,
            e=int(row.e, 16),
            n=int(row.n, 16),
            d=int(row.d, 16),
            bits=row.bits,
            created_at=row.created_at,
        )

    def save(self, keypair: RsaKeyPair) -> RsaKeyPair:
        self.db.merge(
            RsaKeyORM(
                owner_id=keypair.owner_id,
                e=format(keypair.e, "x"),
                n=format(keypair.n, "x"),
                d=format(keypair.d, "x"),
                bits=keypair.bits,
                created_at=keypair.created_at,
            )
        )
        self.db.commit()
        return keypair
