"""Shared test fixtures for Herald tests."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from herald.database import init_db, set_db_path, close_connection
from herald.seed import seed_all


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    """Create a fresh SQLite database for each test."""
    db_path = str(tmp_path / "test_herald.db")
    set_db_path(db_path)
    init_db(db_path)
    seed_all()
    yield db_path
    close_connection()


@pytest.fixture
def client(fresh_db):
    """FastAPI TestClient with a fresh seeded database."""
    from herald.main import app
    with TestClient(app) as c:
        yield c
