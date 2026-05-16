from pydantic import BaseModel


class PoolPlanAction(BaseModel):
    action: str
    detail: str


class PoolPlanResponse(BaseModel):
    pool_id: int
    desired_size: int
    vmid_preview: list[int]
    naming_preview: list[str]
    warnings: list[str]
    estimated_actions: list[PoolPlanAction]
