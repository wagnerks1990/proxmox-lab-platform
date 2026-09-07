from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import require_role
from app.db.session import get_db
from app.schemas.common import ApiEnvelope
from app.schemas.reconciliation import ReconciliationSummary, ReconciliationPreview
from app.services.reconciliation_planning_service import ReconciliationPlanningService
from app.services.organization_access import OrganizationContext, get_current_organization

router = APIRouter()


@router.get('/admin/reconciliation/summary', response_model=ApiEnvelope[ReconciliationSummary])
def reconciliation_summary(_user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    return ApiEnvelope(success=True, data=ReconciliationPlanningService(db).summary(organization.id))


@router.post('/admin/reconciliation/preview', response_model=ApiEnvelope[ReconciliationPreview])
def reconciliation_preview(_user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    return ApiEnvelope(success=True, data=ReconciliationPlanningService(db).preview(organization.id))
