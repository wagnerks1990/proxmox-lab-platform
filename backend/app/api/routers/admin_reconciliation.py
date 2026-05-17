from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import require_role
from app.db.session import get_db
from app.schemas.common import ApiEnvelope
from app.schemas.reconciliation import ReconciliationSummary, ReconciliationPreview
from app.services.reconciliation_planning_service import ReconciliationPlanningService

router = APIRouter()


@router.get('/admin/reconciliation/summary', response_model=ApiEnvelope[ReconciliationSummary])
def reconciliation_summary(_user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    return ApiEnvelope(success=True, data=ReconciliationPlanningService(db).summary())


@router.post('/admin/reconciliation/preview', response_model=ApiEnvelope[ReconciliationPreview])
def reconciliation_preview(_user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    return ApiEnvelope(success=True, data=ReconciliationPlanningService(db).preview())
