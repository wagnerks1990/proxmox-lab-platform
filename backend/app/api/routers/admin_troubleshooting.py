from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.schemas.common import ApiEnvelope
from app.services.telemetry_service import TelemetryService
from app.services.worker_run_service import WorkerRunService

router = APIRouter()


@router.get('/admin/troubleshooting/recent', response_model=ApiEnvelope[list[dict]])
def recent_issues(_user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    out = []
    for e in TelemetryService(db).recent_events(severity='error', limit=20):
        out.append({'issue_type': e.event_type, 'severity': e.severity, 'timestamp': e.created_at, 'probable_cause': 'Runtime or integration failure', 'suggested_fix': 'Inspect service logs and retry launch.'})
    for r in WorkerRunService(db).recent(20):
        if r.status == 'failed':
            out.append({'issue_type': f'worker:{r.worker_name}', 'severity': 'error', 'timestamp': r.started_at, 'probable_cause': r.error or 'Worker failure', 'suggested_fix': 'Review worker summary and scheduler health.'})
    return ApiEnvelope(success=True, data=out[:50])
