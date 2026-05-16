from pydantic import BaseModel


class RuntimeSummary(BaseModel):
    scheduler_enabled: bool
    scheduler_running: bool
    db_status: str
    telemetry_status: str
    event_stream_status: str
    recent_worker_failures: int
    stale_worker_warnings: int
    recent_session_cleanup_status: str
    overall_status: str
