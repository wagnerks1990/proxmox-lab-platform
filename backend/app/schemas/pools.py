from datetime import datetime
from pydantic import BaseModel


class PoolBase(BaseModel):
    name: str
    description: str | None = None
    pool_type: str
    template_vmid: int | None = None
    template_node: str | None = None
    default_protocol: str
    target_node: str | None = None
    storage: str | None = None
    bridge: str | None = None
    vlan_tag: int | None = None
    vmid_start: int | None = None
    vmid_end: int | None = None
    naming_pattern: str | None = None
    desired_size: int = 0
    maintenance_mode: bool = False
    enabled: bool = True


class PoolCreate(PoolBase):
    pass


class PoolPatch(BaseModel):
    description: str | None = None
    default_protocol: str | None = None
    desired_size: int | None = None
    maintenance_mode: bool | None = None
    enabled: bool | None = None


class PoolOut(PoolBase):
    id: int
    created_at: datetime
    updated_at: datetime
    linked_vm_count: int | None = None
    linked_template_count: int | None = None
    linked_group_count: int | None = None
    readiness_status: str | None = None
    placement_warning: str | None = None
    asset_ready_nodes: list[str] | None = None
    constrained_nodes: list[str] | None = None
    missing_templates_by_node: dict | None = None
    missing_isos_by_node: dict | None = None
    recommended_next_steps: list[str] | None = None
