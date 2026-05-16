from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.config import settings
from app.db.session import get_db
from app.schemas.common import ApiEnvelope
from app.services.worker_run_service import WorkerRunService
from app.workers.scheduler import scheduler

router = APIRouter()


@router.get('/admin/operations/health', response_model=ApiEnvelope[dict])
def operations_health(_user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    db_ok = True
    try:
        db.execute(text('SELECT 1'))
    except Exception:
        db_ok = False
    recent = WorkerRunService(db).recent(20)
    failed = [r for r in recent if r.status == 'failed']
    return ApiEnvelope(success=True, data={
        'backend': 'ok',
        'database': 'ok' if db_ok else 'error',
        'scheduler_enabled': settings.worker_scheduler_enabled,
        'scheduler_running': bool(scheduler and scheduler.running),
        'worker_recent_failures': len(failed),
        'telemetry_storage': 'configured',
        'guacamole_health': 'unknown',
        'proxmox_health': 'unknown',
        'session_cleanup_status': 'scheduled' if settings.worker_scheduler_enabled else 'disabled',
    })
