"""Test fixtures: an isolated SQLite DB per test session, with lookups seeded."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Dosage, Medication


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # single shared in-memory connection
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    # Seed the lookup tables the prescription routes validate against.
    with TestingSession() as db:
        db.add_all([Medication(name="Prozac"), Medication(name="Lexapro")])
        db.add_all([Dosage(value="5mg"), Dosage(value="10mg")])
        db.commit()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # No context manager: tests provide their own schema via the override above,
    # so we skip the app lifespan (which would init/seed the real database).
    yield TestClient(app)
    app.dependency_overrides.clear()
