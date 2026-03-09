from __future__ import annotations

import os
from pathlib import Path

import pytest

# Ensure deterministic test database before app imports
os.environ.setdefault("MUP_DATABASE_URL", "sqlite:///./platform/tests/test.db")
os.environ.setdefault("MUP_SCHEDULER_ENABLED", "false")

from app.db import Base, SessionLocal, engine


def _db_file_from_url() -> Path | None:
    url = os.environ.get("MUP_DATABASE_URL", "")
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return None
    return Path(url.removeprefix(prefix))


@pytest.fixture(autouse=True)
def reset_db():
    engine.dispose()
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    yield
    engine.dispose()


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    yield
    engine.dispose()
    db_file = _db_file_from_url()
    if db_file and db_file.exists():
        try:
            db_file.unlink()
        except PermissionError:
            pass
