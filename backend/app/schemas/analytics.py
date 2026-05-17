from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    sessions_by_state: dict[str, int]
    sessions_by_protocol: dict[str, int]
    telemetry_by_severity: dict[str, int]
    worker_runs_by_status: dict[str, int]
    pools_by_type: dict[str, int]
    pools_by_status: dict[str, int]
    launch_failures: int
    reconnect_failures: int
    stale_sessions: int
    active_sessions: int
    recent_failure_count: int
