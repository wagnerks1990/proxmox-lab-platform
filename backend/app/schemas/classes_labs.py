from datetime import datetime
from pydantic import BaseModel


class ClassBase(BaseModel):
    name: str
    term: str | None = None
    instructor_id: int | None = None
    join_code: str | None = None


class ClassCreate(ClassBase):
    pass


class ClassPatch(BaseModel):
    name: str | None = None
    term: str | None = None
    instructor_id: int | None = None
    join_code: str | None = None


class ClassOut(ClassBase):
    id: int
    created_at: datetime
    updated_at: datetime


class EnrollmentCreate(BaseModel):
    user_id: int
    role: str | None = None


class EnrollmentOut(BaseModel):
    id: int
    class_id: int
    user_id: int
    role: str | None = None
    created_at: datetime


class LabBase(BaseModel):
    class_id: int
    name: str
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    default_pool_id: int
    student_can_reset: bool = False
    student_can_power_off: bool = False
    terminal_enabled: bool = False
    console_enabled: bool = False
    rdp_enabled: bool = False


class LabCreate(LabBase):
    pass


class LabPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    default_pool_id: int | None = None
    student_can_reset: bool | None = None
    student_can_power_off: bool | None = None
    terminal_enabled: bool | None = None
    console_enabled: bool | None = None
    rdp_enabled: bool | None = None


class LabOut(LabBase):
    id: int
    created_at: datetime
    updated_at: datetime
    readiness_status: str | None = None
    placement_warning: str | None = None
    asset_ready_nodes: list[str] | None = None
    constrained_nodes: list[str] | None = None
    missing_templates_by_node: dict | None = None
    missing_isos_by_node: dict | None = None
    missing_ct_templates_by_node: dict | None = None
    vm_template_vmid_by_node: dict | None = None
    recommended_next_steps: list[str] | None = None
    assets_page_hint: str | None = None
