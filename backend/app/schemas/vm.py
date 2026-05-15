from datetime import datetime
from pydantic import BaseModel


class TemplateResponse(BaseModel):
    id: int
    name: str
    proxmox_node: str
    source_vmid: int
    enabled: bool = True


class TemplateCreateRequest(BaseModel):
    name: str
    proxmox_node: str
    source_vmid: int
    enabled: bool = True


class TemplateUpdateRequest(BaseModel):
    name: str | None = None
    proxmox_node: str | None = None
    source_vmid: int | None = None
    enabled: bool | None = None


class CreateVMRequest(BaseModel):
    template_id: int
    lab_name: str
    auto_start: bool = True


class VMResponse(BaseModel):
    id: int
    vm_name: str
    vmid: int
    status: str
    proxmox_node: str
    created_at: datetime | None = None
    operating_system: str | None = None
    access_protocols: str | None = None
    ssh_enabled: bool | None = None
    rdp_enabled: bool | None = None
    spice_enabled: bool | None = None
    console_enabled: bool | None = None
    default_username: str | None = None
    assigned_ip: str | None = None
    hostname: str | None = None
    ssh_username: str | None = None
    ssh_auth_method: str | None = None
    ssh_port: int | None = 22


class VMCreateResponse(VMResponse):
    message: str | None = None


class AuditLogResponse(BaseModel):
    id: int
    actor_id: int
    action: str
    target_type: str
    target_id: str
    created_at: datetime | None = None
