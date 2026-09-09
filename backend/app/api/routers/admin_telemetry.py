from datetime import datetime
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.schemas.common import ApiEnvelope
from app.schemas.telemetry import TelemetryEventOut
from app.services.telemetry_service import TelemetryService
from app.telemetry.lifecycle_metrics import as_dict

router = APIRouter()


@router.get("/admin/telemetry/summary", response_model=ApiEnvelope[dict])
def telemetry_summary(
    request: Request,
    _user=Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    summary = TelemetryService(db).summary_counts()
    summary["in_memory"] = as_dict()
    return ApiEnvelope(
        success=True,
        data=summary,
        message="ok",
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/admin/telemetry/events", response_model=ApiEnvelope[list[TelemetryEventOut]]
)
def telemetry_events(
    event_type: str | None = None,
    severity: str | None = None,
    user_id: int | None = None,
    vm_id: int | None = None,
    session_id: int | None = None,
    since: datetime | None = None,
    limit: int = 100,
    _user=Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    rows = TelemetryService(db).recent_events(
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        vm_id=vm_id,
        session_id=session_id,
        since=since,
        limit=limit,
    )
    return ApiEnvelope(success=True, data=rows)
