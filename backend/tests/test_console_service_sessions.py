import pytest
from fastapi import HTTPException

from app.services.console_service import ConsoleService


class DummyDB:
    def add(self, *_args, **_kwargs):
        return None


class DummySessionSvc:
    def __init__(self):
        self.failed = False
        self.active = False
        self._id = 1

    def create_launch(self, *_args, **_kwargs):
        class O: id = 1
        return O()

    def create_launching_session(self, *_args, **_kwargs):
        class O: id = 2
        return O()

    def mark_failed(self, *_args, **_kwargs):
        self.failed = True
        return True

    def mark_active(self, *_args, **_kwargs):
        self.active = True
        return True


class U: id = 1; role = type('R', (), {'name': 'Admin'})()
class V: id = 1; vmid = 100; proxmox_node='n1'; ssh_enabled=False; assigned_ip=None


@pytest.mark.asyncio
async def test_failed_launch_creates_failed_session(monkeypatch):
    svc = ConsoleService(DummyDB())
    svc.sessions = DummySessionSvc()
    with pytest.raises(HTTPException):
        await svc.terminal_url(U(), V())
    assert svc.sessions.failed
