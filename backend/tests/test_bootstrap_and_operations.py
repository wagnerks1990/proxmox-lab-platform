from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.models.models import Role
from app.services.operation_service import (
    allocate_vmid,
    claim_operation,
    enqueue_operation,
    safe_vm_name,
)


def _database():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def test_first_run_bootstrap_is_one_time_and_sets_http_only_cookie(monkeypatch):
    engine, db = _database()
    db.add_all([Role(name="Student"), Role(name="Teacher"), Role(name="Admin")])
    db.commit()
    monkeypatch.setattr(settings, "bootstrap_admin_token", "one-time-bootstrap-secret")

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(
        app,
        headers={"Origin": "http://testserver", "Sec-Fetch-Site": "same-origin"},
    )
    try:
        assert client.get("/api/bootstrap/status").json()["bootstrap_required"] is True
        response = client.post(
            "/api/bootstrap/admin",
            json={
                "token": "one-time-bootstrap-secret",
                "username": "first-admin",
                "email": "admin@example.edu",
                "password": "Correct-Horse-7!",
            },
        )
        assert response.status_code == 204, response.text
        assert response.content == b""
        assert "httponly" in response.headers["set-cookie"].lower()
        assert "samesite=strict" in response.headers["set-cookie"].lower()
        assert client.get("/api/auth/me").json()["username"] == "first-admin"
        assert (
            client.post(
                "/api/bootstrap/admin",
                json={
                    "token": "one-time-bootstrap-secret",
                    "username": "second-admin",
                    "email": "second@example.edu",
                    "password": "Correct-Horse-8!",
                },
            ).status_code
            == 409
        )
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(engine)


def test_vmid_allocator_and_expired_lease_recovery():
    engine, db = _database()
    try:
        assert allocate_vmid(db) == 200000
        assert allocate_vmid(db) == 200001
        operation = enqueue_operation(
            db,
            organization_id=None,
            requested_by=None,
            operation_type="vm.start",
            target_type="student_vm",
            target_id="42",
            payload={},
            idempotency_key="test-operation",
        )
        db.commit()
        claimed = claim_operation(db, "worker-one")
        assert claimed.id == operation.id
        assert claimed.state == "running"
        claimed.lease_expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
        reclaimed = claim_operation(db, "worker-two")
        assert reclaimed.id == operation.id
        assert reclaimed.attempts == 2
        assert (
            safe_vm_name("Student Name", "Routing / VLAN Lab", 200001)
            == "student-name-routing-vlan-lab-200001"
        )
    finally:
        db.close()
        Base.metadata.drop_all(engine)
