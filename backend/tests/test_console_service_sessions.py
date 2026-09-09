import pytest
from fastapi import HTTPException

from app.services.console_service import ConsoleService


class DummyDB:
    def __init__(self):
        self.added = []

    def add(self, *_args, **_kwargs):
        self.added.extend(_args)


class U:
    id = 1
    role_rel = type("R", (), {"name": "Admin"})()


class V:
    id = 1
    vmid = 100
    proxmox_node = "n1"
    ssh_enabled = False
    assigned_ip = None


@pytest.mark.asyncio
async def test_failed_http_launch_does_not_create_session():
    db = DummyDB()
    svc = ConsoleService(db)
    with pytest.raises(HTTPException):
        await svc.terminal_url(U(), V())
    assert db.added == []
