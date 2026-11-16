"""Connexion SQLAlchemy : un moteur, une fabrique de sessions, une dépendance FastAPI."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    # pool_pre_ping : évite d'utiliser une connexion coupée (redémarrage de PostgreSQL)
    return create_engine(url, pool_pre_ping=True)


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Dépendance FastAPI : une session par requête, toujours refermée."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
