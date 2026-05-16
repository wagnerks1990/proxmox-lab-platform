from fastapi import APIRouter, Depends, Request

from app.api.deps import require_role
from app.schemas.common import ApiEnvelope
from app.telemetry.lifecycle_metrics import as_dict

router = APIRouter()


@router.get('/admin/telemetry/summary', response_model=ApiEnvelope[dict])
def telemetry_summary(request: Request, _user=Depends(require_role('Teacher', 'Admin'))):
    return ApiEnvelope(success=True, data=as_dict(), message='ok', request_id=getattr(request.state, 'request_id', None))
