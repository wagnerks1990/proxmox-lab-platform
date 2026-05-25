from datetime import datetime

import pytest
from fastapi import HTTPException

from app.api.routers import admin_events
from app.models.models import AuditLog, TelemetryEvent, WorkerRun


class Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeQuery:
    def __init__(self, rows, fail=False):
        self.rows = rows
        self.fail = fail

    def filter(self, *args, **kwargs):
        if self.fail:
            raise RuntimeError("query failure")
        return self

    def order_by(self, *args, **kwargs):
        if self.fail:
            raise RuntimeError("query failure")
        return self

    def limit(self, *args, **kwargs):
        if self.fail:
            raise RuntimeError("query failure")
        return self

    def all(self):
        if self.fail:
            raise RuntimeError("query failure")
        return self.rows


class FakeDB:
    def __init__(self, mapping=None, fail_models=None):
        self.mapping = mapping or {}
        self.fail_models = set(fail_models or [])

    def query(self, model):
        fail = model in self.fail_models
        rows = self.mapping.get(model, [])
        return FakeQuery(rows, fail=fail)


def _set_role(monkeypatch, role_name):
    monkeypatch.setattr(admin_events, "get_role_name", lambda _user: role_name)


def test_admin_events_worker_runs_serialization(monkeypatch):
    _set_role(monkeypatch, "Admin")

    wr_rows = [
        Obj(id=1, worker_name="health_worker", status="ok", started_at=datetime(2026, 5, 24, 10, 0, 0), request_id="req-1"),
        Obj(id=2, worker_name="cleanup_worker", status="running", started_at=datetime(2026, 5, 24, 11, 0, 0), request_id=None),
    ]
    db = FakeDB(mapping={WorkerRun: wr_rows})

    result = admin_events.list_events(limit=5, offset=0, _user=Obj(), db=db)

    assert set(result.keys()) == {"items", "total", "limit", "offset"}
    assert result["limit"] == 5
    assert result["offset"] == 0
    assert result["total"] >= 2
    worker_items = [i for i in result["items"] if i["source"] == "worker_runs"]
    assert len(worker_items) == 2
    assert worker_items[0]["message"] in {"health_worker", "cleanup_worker"}
    assert all("name" not in i for i in worker_items)


def test_admin_events_worker_runs_null_odd_values(monkeypatch):
    _set_role(monkeypatch, "Admin")

    wr_rows = [
        Obj(id=3, worker_name=None, status=None, started_at=None, request_id=None),
        Obj(id=4, worker_name="", status="WEIRD_STATUS", started_at=None, request_id=""),
    ]
    db = FakeDB(mapping={WorkerRun: wr_rows})

    result = admin_events.list_events(limit=10, offset=0, _user=Obj(), db=db)

    worker_items = [i for i in result["items"] if i["source"] == "worker_runs"]
    assert len(worker_items) == 2
    assert any(i["message"].startswith("Worker run") for i in worker_items)
    assert all(i["time"] for i in worker_items)
    assert all(i["type"] == "task" for i in worker_items)


def test_admin_events_source_isolation_audit_failure(monkeypatch):
    _set_role(monkeypatch, "Admin")

    tel_rows = [Obj(id=9, created_at=datetime(2026, 5, 24, 12, 0, 0), severity="warning", event_type="node_issue", vm_id=None)]
    wr_rows = [Obj(id=5, worker_name="session_worker", status="ok", started_at=datetime(2026, 5, 24, 13, 0, 0), request_id="req-5")]
    db = FakeDB(mapping={TelemetryEvent: tel_rows, WorkerRun: wr_rows}, fail_models={AuditLog})

    result = admin_events.list_events(limit=20, offset=0, _user=Obj(), db=db)

    sources = {i["source"] for i in result["items"]}
    assert "worker_runs" in sources
    assert "telemetry_events" in sources


def test_admin_events_source_isolation_telemetry_failure(monkeypatch):
    _set_role(monkeypatch, "Admin")

    audit_rows = [Obj(id=10, created_at=datetime(2026, 5, 24, 12, 0, 0), action="updated", target_type="vm", target_id=101)]
    wr_rows = [Obj(id=6, worker_name="cleanup_worker", status="error", started_at=datetime(2026, 5, 24, 14, 0, 0), request_id="req-6")]
    db = FakeDB(mapping={AuditLog: audit_rows, WorkerRun: wr_rows}, fail_models={TelemetryEvent})

    result = admin_events.list_events(limit=20, offset=0, _user=Obj(), db=db)

    sources = {i["source"] for i in result["items"]}
    assert "worker_runs" in sources
    assert "audit_logs" in sources


def test_admin_events_source_isolation_worker_failure(monkeypatch):
    _set_role(monkeypatch, "Admin")

    audit_rows = [Obj(id=11, created_at=datetime(2026, 5, 24, 12, 0, 0), action="created", target_type="pool", target_id=1)]
    tel_rows = [Obj(id=12, created_at=datetime(2026, 5, 24, 12, 1, 0), severity="info", event_type="heartbeat", vm_id=None)]
    db = FakeDB(mapping={AuditLog: audit_rows, TelemetryEvent: tel_rows}, fail_models={WorkerRun})

    result = admin_events.list_events(limit=20, offset=0, _user=Obj(), db=db)

    sources = {i["source"] for i in result["items"]}
    assert "audit_logs" in sources
    assert "telemetry_events" in sources
    assert "worker_runs" not in sources


def test_admin_events_rbac_admin_and_teacher_allowed(monkeypatch):
    db = FakeDB()

    _set_role(monkeypatch, "Admin")
    assert admin_events.list_events(limit=1, offset=0, _user=Obj(), db=db)["limit"] == 1

    _set_role(monkeypatch, "Teacher")
    assert admin_events.list_events(limit=1, offset=0, _user=Obj(), db=db)["limit"] == 1


def test_admin_events_rbac_student_forbidden(monkeypatch):
    _set_role(monkeypatch, "Student")
    db = FakeDB()

    with pytest.raises(HTTPException) as exc:
        admin_events.list_events(limit=1, offset=0, _user=Obj(), db=db)

    assert exc.value.status_code == 403
