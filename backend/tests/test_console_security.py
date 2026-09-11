import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routers import admin_events
from app.db.session import Base
from app.models.models import (
    Class,
    DesktopPool,
    Lab,
    LabAssignment,
    LabRun,
    Organization,
    OrganizationMembership,
    Role,
    StudentVM,
    User,
    VMTemplate,
)
from app.services.console_access import get_console_vm_for_user
from app.services.console_ws_service import ConsoleWsService
from app.services.organization_access import OrganizationContext


def _two_instructor_console_data(db):
    role = Role(name="Student")
    db.add(role)
    db.flush()
    instructor_a = User(
        username="console-instructor-a",
        email="console-a@example.test",
        password_hash="unused",
        role_id=role.id,
        is_active=True,
    )
    instructor_b = User(
        username="console-instructor-b",
        email="console-b@example.test",
        password_hash="unused",
        role_id=role.id,
        is_active=True,
    )
    student = User(
        username="console-student",
        email="console-student@example.test",
        password_hash="unused",
        role_id=role.id,
        is_active=True,
    )
    db.add_all([instructor_a, instructor_b, student])
    db.flush()
    organization = Organization(name="Console org", slug="console-org", enabled=True)
    db.add(organization)
    db.flush()
    db.add_all(
        [
            OrganizationMembership(
                organization_id=organization.id,
                user_id=instructor.id,
                role="instructor",
                is_active=True,
            )
            for instructor in (instructor_a, instructor_b)
        ]
    )
    template = VMTemplate(
        organization_id=organization.id,
        name="console-template",
        proxmox_node="pve-test",
        source_vmid=9000,
    )
    pool = DesktopPool(
        organization_id=organization.id,
        name="console-pool",
        pool_type="lab",
        default_protocol="novnc",
    )
    db.add_all([template, pool])
    db.flush()
    classes = [
        Class(
            organization_id=organization.id,
            name=f"Console class {suffix}",
            instructor_id=instructor.id,
        )
        for suffix, instructor in (("A", instructor_a), ("B", instructor_b))
    ]
    db.add_all(classes)
    db.flush()
    labs = [
        Lab(
            organization_id=organization.id,
            class_id=classroom.id,
            name=f"Console lab {index}",
            default_pool_id=pool.id,
            console_enabled=True,
        )
        for index, classroom in enumerate(classes)
    ]
    db.add_all(labs)
    db.flush()
    runs = [
        LabRun(
            organization_id=organization.id,
            lab_id=lab.id,
            name=f"Console run {index}",
            state="active",
            created_by=instructor.id,
        )
        for index, (lab, instructor) in enumerate(
            zip(labs, (instructor_a, instructor_b), strict=True)
        )
    ]
    db.add_all(runs)
    db.flush()
    vms = [
        StudentVM(
            organization_id=organization.id,
            owner_id=student.id,
            template_id=template.id,
            vm_name=f"console-vm-{index}",
            vmid=8100 + index,
            proxmox_node="pve-test",
            status="running",
        )
        for index in range(2)
    ]
    db.add_all(vms)
    db.flush()
    db.add_all(
        [
            LabAssignment(
                organization_id=organization.id,
                lab_run_id=run.id,
                user_id=student.id,
                template_id=template.id,
                slot_index=1,
                status="ready",
                student_vm_id=vm.id,
            )
            for run, vm in zip(runs, vms, strict=True)
        ]
    )
    db.commit()
    return organization, (instructor_a, instructor_b), vms


def test_console_access_is_scoped_to_instructors_own_class():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        organization, instructors, vms = _two_instructor_console_data(db)
        context = OrganizationContext(organization.id, organization.slug, "instructor")
        assert (
            get_console_vm_for_user(
                db,
                user=instructors[0],
                vm_id=vms[0].id,
                organization=context,
                operation="console",
            ).id
            == vms[0].id
        )
        with pytest.raises(HTTPException) as denied_a:
            get_console_vm_for_user(
                db,
                user=instructors[0],
                vm_id=vms[1].id,
                organization=context,
                operation="console",
            )
        assert denied_a.value.status_code == 404
        with pytest.raises(HTTPException) as denied_b:
            get_console_vm_for_user(
                db,
                user=instructors[1],
                vm_id=vms[0].id,
                organization=context,
                operation="console",
            )
        assert denied_b.value.status_code == 404
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_console_watchdog_closes_when_original_session_is_revoked(monkeypatch):
    class FakeWebSocket:
        closed = None

        async def close(self, code, reason):
            self.closed = (code, reason)

    async def no_wait(_seconds):
        return None

    def revoked(_token, _db):
        raise HTTPException(status_code=401, detail="Invalid token")

    websocket = FakeWebSocket()
    db = SimpleNamespace(expire_all=lambda: None)
    monkeypatch.setattr("app.services.console_ws_service.asyncio.sleep", no_wait)
    monkeypatch.setattr("app.services.console_ws_service.get_user_from_token", revoked)
    asyncio.run(
        ConsoleWsService(db)._watch_session_access(
            websocket,
            SimpleNamespace(heartbeat=lambda _session_id: True),
            1,
            SimpleNamespace(id=1),
            SimpleNamespace(id=2),
            "console",
            "revoked-token",
            3,
        )
    )
    assert websocket.closed == (1008, "Console access revoked")


def test_sse_revalidation_rejects_revoked_original_session(monkeypatch):
    fake_db = SimpleNamespace(close=lambda: None)
    monkeypatch.setattr(admin_events, "SessionLocal", lambda: fake_db)

    def revoked(_token, _db):
        raise HTTPException(status_code=401, detail="Invalid token")

    monkeypatch.setattr(admin_events, "get_user_from_token", revoked)
    assert not admin_events._sse_access_allowed("revoked-token", 1)
