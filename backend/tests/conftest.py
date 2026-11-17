"""Fixtures : base de test chargée avec le VRAI fichier NOAA via l'ETL.

Par défaut : SQLite en mémoire (aucune installation requise).
Pour tester sur PostgreSQL (recommandé, identique à la production) :
    TEST_DATABASE_URL=postgresql+psycopg://enso:enso_dev@localhost:5432/enso_test pytest
"""

import os
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import app
from etl.load import load_bytes

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "raw" / "oni.ascii.txt"
TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")


@pytest.fixture(scope="session")
def oni_text() -> str:
    return DATA_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def engine():
    if TEST_DB_URL.startswith("sqlite"):
        eng = create_engine(
            TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    else:
        eng = create_engine(TEST_DB_URL)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture(scope="session")
def session_factory(engine):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        load_bytes(
            session,
            DATA_FILE.read_bytes(),
            file_name=DATA_FILE.name,
            extracted_at=date(2026, 11, 16),
            last_modified="Tue, 03 Nov 2026 19:31:48 GMT",
        )
    return factory


@pytest.fixture()
def client(session_factory):
    def override():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
