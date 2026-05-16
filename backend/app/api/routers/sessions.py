from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.schemas.session import SessionActivityResponse
from app.services.session_service import SessionService

router = APIRouter()


@router.get('/admin/session-activity', response_model=list[SessionActivityResponse])
def session_activity(user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    return SessionService(db).get_recent_activity(200)
