from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.common import ApiEnvelope
from app.schemas.reconciliation import ReconciliationSummary, ReconciliationPreview
from app.services.reconciliation_planning_service import ReconciliationPlanningService
from app.services.organization_access import (
    OrganizationContext,
    require_organization_role,
)

router = APIRouter()


@router.get(
    "/admin/reconciliation/summary", response_model=ApiEnvelope[ReconciliationSummary]
)
def reconciliation_summary(
    _user=Depends(get_current_user),
    db: Session = Depends(get_db),
    organization: OrganizationContext = Depends(
        require_organization_role("instructor")
    ),
):
    return ApiEnvelope(
        success=True, data=ReconciliationPlanningService(db).summary(organization.id)
    )


@router.post(
    "/admin/reconciliation/preview", response_model=ApiEnvelope[ReconciliationPreview]
)
def reconciliation_preview(
    _user=Depends(get_current_user),
    db: Session = Depends(get_db),
    organization: OrganizationContext = Depends(
        require_organization_role("instructor")
    ),
):
    return ApiEnvelope(
        success=True, data=ReconciliationPlanningService(db).preview(organization.id)
    )
