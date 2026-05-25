from pydantic import BaseModel


class SyncIsoRequest(BaseModel):
    filename: str
    storage_id: str = 'local'
    source_url: str
    target_nodes: list[str]


class SyncCtTemplateRequest(BaseModel):
    filename: str
    storage_id: str = 'local'
    source_url: str
    target_nodes: list[str]


class SyncVmTemplateRequest(BaseModel):
    source_node: str
    source_vmid: int
    template_name: str
    storage_id: str = 'local-lvm'
    target_nodes: list[str]
