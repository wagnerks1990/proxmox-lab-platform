from datetime import datetime
from pydantic import BaseModel


class TelemetryEventOut(BaseModel):
    id: int
    event_type: str
    severity: str
    source: str
    user_id: int | None
    vm_id: int | None
    session_id: int | None
    request_id: str | None
    metadata_json: str | None
    created_at: datetime


class TelemetrySummary(BaseModel):
    total_events: int
    failures: int
    session_events: int
