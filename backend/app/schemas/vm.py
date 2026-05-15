from datetime import datetime
from pydantic import BaseModel


class TemplateResponse(BaseModel):
    id: int
    name: str
    proxmox_node: str
    source_vmid: int
    operating_system: str | None = None
    default_protocols: str | None = None
    description: str | None = None
    enabled: bool = True


class TemplateCreateRequest(BaseModel):
    name: str
    proxmox_node: str
    source_vmid: int
    operating_system: str | None = None
    default_protocols: str | None = None
    description: str | None = None
    enabled: bool = True


class TemplateUpdateRequest(BaseModel):
    name: str | None = None
    proxmox_node: str | None = None
    source_vmid: int | None = None
    operating_system: str | None = None
    default_protocols: str | None = None
    description: str | None = None
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


class ConnectionLaunchResponse(BaseModel):
    id: int
    actor_id: int
    vm_id: int
    protocol: str
    status: str
    details: str | None = None
    created_at: datetime | None = None

class PoolBase(BaseModel):
    name: str
    description: str | None = None
    enabled: bool = True
    default_template_id: int | None = None
    max_vms: int = 20
    max_running_vms: int = 10
    auto_start: bool = True
    recycle_on_logout: bool = False
    cluster_id: int | None = None
    node_id: int | None = None
    storage_pool: str | None = None
    network_bridge: str | None = None
    placement_strategy: str | None = 'any_enabled_node'
    preferred_node_id: int | None = None
    resource_pool_id: int | None = None


class PoolResponse(PoolBase):
    id: int
    created_at: datetime | None = None


class GroupResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    created_at: datetime | None = None


class GroupCreateRequest(BaseModel):
    name: str
    description: str | None = None


class GroupUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class GroupMemberRequest(BaseModel):
    user_id: int


class ProtocolSettingsResponse(BaseModel):
    id: int
    terminal_gateway_url: str | None = None
    enable_web_terminal: bool = True
    enable_rdp: bool = True
    enable_spice: bool = True
    enable_novnc: bool = True
    default_ssh_port: int = 22

class ProxmoxClusterBase(BaseModel):
    name: str
    api_url: str
    enabled: bool = True
    description: str | None = None


class ProxmoxClusterResponse(ProxmoxClusterBase):
    id: int
    created_at: datetime | None = None


class ProxmoxNodeBase(BaseModel):
    cluster_id: int
    node_name: str
    management_ip: str | None = None
    enabled: bool = True


class ProxmoxNodeResponse(ProxmoxNodeBase):
    id: int
    status: str | None = None
    last_seen: datetime | None = None
    cpu_usage: str | None = None
    memory_usage: str | None = None
    storage_summary: str | None = None
    created_at: datetime | None = None
