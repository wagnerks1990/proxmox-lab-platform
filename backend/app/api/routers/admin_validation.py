from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import require_role
from app.db.session import get_db
from app.schemas.common import ApiEnvelope
from app.schemas.validation import ValidationCheck
from app.services.validation_service import ValidationService

router = APIRouter()


@router.get(
    "/admin/validation/summary", response_model=ApiEnvelope[list[ValidationCheck]]
)
def validation_summary(
    _user=Depends(require_role("Admin")), db: Session = Depends(get_db)
):
    return ApiEnvelope(success=True, data=ValidationService(db).run_checks())


@router.post("/admin/validation/run", response_model=ApiEnvelope[list[ValidationCheck]])
def validation_run(_user=Depends(require_role("Admin")), db: Session = Depends(get_db)):
    return ApiEnvelope(success=True, data=ValidationService(db).run_checks())
