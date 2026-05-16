from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.schemas.common import ApiEnvelope
from app.services.troubleshooting_service import TroubleshootingService

router = APIRouter()


@router.get('/admin/troubleshooting/recent', response_model=ApiEnvelope[list[dict]])
def recent_issues(_user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    return ApiEnvelope(success=True, data=TroubleshootingService(db).recent())
