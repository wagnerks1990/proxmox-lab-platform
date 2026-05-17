from pydantic import BaseModel


class ReconciliationSummary(BaseModel):
    pools_total: int
    stale_sessions: int
    warnings: int


class ReconciliationPreview(BaseModel):
    missing_desktops: int
    excess_desktops: int
    stopped_desktops: int
    unassigned_desktops: int
    stale_sessions: int
    invalid_pool_config: int
    validation_warnings: int
    proposed_actions: list[str]
