"""
INFRASTRUCTURE - Modèle ORM des clés RSA.
Les grands entiers sont stockés en hexadécimal (texte).
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class RsaKeyORM(Base):
    __tablename__ = "rsa_keys"

    owner_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    e: Mapped[str] = mapped_column(Text)
    n: Mapped[str] = mapped_column(Text)
    d: Mapped[str] = mapped_column(Text)
    bits: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime)
