"""
CORE - Base de données (SQLAlchemy + SQLite)
"""
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # PostgreSQL : vérifie les connexions avant usage (le serveur peut les couper)
    engine = create_engine(
        settings.DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=5, pool_recycle=1800
    )

if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """Dépendance FastAPI : une session par requête."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Crée les tables (import des modèles ORM pour les enregistrer sur Base)."""
    from src.modules.auth.infrastructure import models as _auth  # noqa: F401
    from src.modules.chat.infrastructure import models as _chat  # noqa: F401
    from src.modules.crypt.infrastructure import models as _crypt  # noqa: F401

    Base.metadata.create_all(bind=engine)
