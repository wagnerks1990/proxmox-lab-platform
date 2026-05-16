from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.schemas.vm import AuditLogResponse
from app.services.audit_service import recent_audit_logs
from app.architecture.policies import can_view_audit_logs, PolicyError

router = APIRouter()


@router.get('/admin/audit-logs', response_model=list[AuditLogResponse])
def audit_logs(user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    try:
        can_view_audit_logs(user)
    except PolicyError as exc:
        raise HTTPException(status_code=403, detail={'error': str(exc)})
    return recent_audit_logs(db)
