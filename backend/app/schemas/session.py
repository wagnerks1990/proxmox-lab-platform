from datetime import datetime
from pydantic import BaseModel


class SessionActivityResponse(BaseModel):
    id: int
    user_id: int
    vm_id: int
    protocol: str
    state: str
    node: str | None = None
    proxmox_vmid: int | None = None
    failure_reason: str | None = None
    last_heartbeat_at: datetime | None = None
    created_at: datetime | None = None


class SessionCreateResponse(BaseModel):
    id: int
    state: str
    protocol: str


class SessionHeartbeatRequest(BaseModel):
    state: str | None = None


class SessionHeartbeatResponse(BaseModel):
    id: int
    state: str
    last_heartbeat_at: datetime | None = None
    updated_at: datetime | None = None
