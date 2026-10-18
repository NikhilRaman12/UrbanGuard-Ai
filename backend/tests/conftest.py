import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture()
def store_db(tmp_path, monkeypatch):
    """Give each test an isolated SQLite database."""
    from app import store

    monkeypatch.setattr(store, "DB", tmp_path / "store.db")
    store.init_db()
    return store


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """FastAPI TestClient bound to an isolated database and the real lifespan."""
    from app import store

    monkeypatch.setattr(store, "DB", tmp_path / "api.db")
    store.init_db()

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
