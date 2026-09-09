from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.schemas.common import ApiEnvelope
from app.services.worker_run_service import WorkerRunService

router = APIRouter()


@router.get("/admin/workers/runs", response_model=ApiEnvelope[list[dict]])
def worker_runs(
    limit: int = 100,
    _user=Depends(require_role("Teacher", "Admin")),
    db: Session = Depends(get_db),
):
    rows = WorkerRunService(db).recent(limit)
    return ApiEnvelope(
        success=True,
        data=[
            {
                "id": r.id,
                "worker_name": r.worker_name,
                "status": r.status,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
                "duration_ms": r.duration_ms,
                "summary_json": r.summary_json,
                "error": r.error,
            }
            for r in rows
        ],
    )
