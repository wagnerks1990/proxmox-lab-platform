import asyncio
import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.session import get_db
from app.main import app


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_deploy.py"
SPEC = importlib.util.spec_from_file_location("validate_deploy", MODULE_PATH)
validate_deploy = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validate_deploy)


def test_database_revision_must_equal_expected_head():
    engine = create_engine("sqlite://")
    with Session(engine) as db:
        db.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32))"))
        db.execute(text("INSERT INTO alembic_version VALUES ('expected-head')"))
        db.commit()
        validate_deploy.validate_database_revision(db, "expected-head")
        with pytest.raises(validate_deploy.CheckFailure, match="found"):
            validate_deploy.validate_database_revision(db, "new-head")


def test_ready_and_health_contracts_match_validator(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    db = Session(engine)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(settings, "worker_scheduler_enabled", False)
    monkeypatch.setattr(settings, "worker_lock_backend", "memory")
    monkeypatch.setattr(settings, "replay_store_backend", "memory")
    client = TestClient(app)
    try:
        assert client.get("/api/ready").json() == {"ready": True}
        assert client.get("/api/health").json() == {"status": "ok"}
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_validator_checks_both_http_contracts(monkeypatch):
    class Response:
        status_code = 200
        text = ""

        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    class Client:
        def __init__(self, **_kwargs):
            self.paths = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url):
            if url.endswith("/api/ready"):
                return Response({"ready": True})
            return Response({"status": "ok"})

    monkeypatch.setattr(validate_deploy.httpx, "AsyncClient", Client)
    asyncio.run(validate_deploy.check_health_endpoints())
