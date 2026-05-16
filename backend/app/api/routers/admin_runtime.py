from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import require_role
from app.db.session import get_db
from app.schemas.common import ApiEnvelope
from app.schemas.runtime import RuntimeSummary
from app.services.runtime_supervisor_service import RuntimeSupervisorService

router = APIRouter()


@router.get('/admin/runtime/summary', response_model=ApiEnvelope[RuntimeSummary])
def runtime_summary(_user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    return ApiEnvelope(success=True, data=RuntimeSupervisorService(db).summary())
