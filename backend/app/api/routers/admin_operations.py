import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.config import settings
from app.db.session import get_db
from app.schemas.common import ApiEnvelope
from app.services.worker_run_service import WorkerRunService
from app.models.models import DurableOperation
from app.services.organization_access import (
    OrganizationContext,
    get_current_organization,
    organization_role_at_least,
)

router = APIRouter()


def _operation_out(row: DurableOperation) -> dict:
    return {
        "id": row.id,
        "operation_type": row.operation_type,
        "target_type": row.target_type,
        "target_id": row.target_id,
        "state": row.state,
        "attempts": row.attempts,
        "proxmox_upid": row.proxmox_upid,
        "result": json.loads(row.result_json) if row.result_json else None,
        "error": row.error,
        "created_at": row.created_at,
        "started_at": row.started_at,
        "finished_at": row.finished_at,
    }


@router.get("/operations")
def list_operations(
    limit: int = 50,
    user=Depends(require_role("Student", "Teacher", "Admin")),
    db: Session = Depends(get_db),
    organization: OrganizationContext = Depends(get_current_organization),
):
    q = db.query(DurableOperation).filter(
        DurableOperation.organization_id == organization.id
    )
    if not organization_role_at_least(organization, "instructor"):
        q = q.filter(DurableOperation.requested_by == user.id)
    rows = q.order_by(DurableOperation.id.desc()).limit(max(1, min(limit, 200))).all()
    return {"operations": [_operation_out(row) for row in rows]}


@router.get("/operations/{operation_id}")
def get_operation(
    operation_id: int,
    user=Depends(require_role("Student", "Teacher", "Admin")),
    db: Session = Depends(get_db),
    organization: OrganizationContext = Depends(get_current_organization),
):
    row = (
        db.query(DurableOperation)
        .filter(
            DurableOperation.id == operation_id,
            DurableOperation.organization_id == organization.id,
        )
        .first()
    )
    if not row or (
        not organization_role_at_least(organization, "instructor")
        and row.requested_by != user.id
    ):
        raise HTTPException(status_code=404, detail="Operation not found")
    return _operation_out(row)


@router.get("/admin/operations/health", response_model=ApiEnvelope[dict])
def operations_health(
    _user=Depends(require_role("Teacher", "Admin")), db: Session = Depends(get_db)
):
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    recent = WorkerRunService(db).recent(20)
    failed = [r for r in recent if r.status == "failed"]
    return ApiEnvelope(
        success=True,
        data={
            "backend": "ok",
            "database": "ok" if db_ok else "error",
            "scheduler_enabled": settings.worker_scheduler_enabled,
            "scheduler_running": _scheduler_running(),
            "worker_recent_failures": len(failed),
            "telemetry_storage": "configured",
            "guacamole_health": "unknown",
            "proxmox_health": "unknown",
            "session_cleanup_status": "scheduled"
            if settings.worker_scheduler_enabled
            else "disabled",
        },
    )


def _scheduler_running() -> bool:
    try:
        from app.workers.scheduler import scheduler

        return bool(scheduler and scheduler.running)
    except Exception:
        return False
