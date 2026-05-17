from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.schemas.common import ApiEnvelope
from app.schemas.analytics import AnalyticsSummary
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get('/admin/analytics/summary', response_model=ApiEnvelope[AnalyticsSummary])
def analytics_summary(_user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    return ApiEnvelope(success=True, data=AnalyticsService(db).summary())
