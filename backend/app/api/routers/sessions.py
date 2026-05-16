from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.models import User
from app.schemas.session import SessionActivityResponse, SessionHeartbeatRequest, SessionHeartbeatResponse
from app.services.session_service import SessionService
from app.architecture.state_machines import SessionState

router = APIRouter()


@router.get('/admin/session-activity', response_model=list[SessionActivityResponse])
def session_activity(user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    return SessionService(db).get_recent_activity(200)


@router.post('/sessions/{id}/heartbeat', response_model=SessionHeartbeatResponse)
def session_heartbeat(id: int, payload: SessionHeartbeatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = SessionService(db)
    row = svc.get_session_for_user(id, user)
    if not row:
        raise HTTPException(status_code=404, detail='Session not found')
    next_state = SessionState(payload.state) if payload.state else None
    updated = svc.heartbeat(id, next_state)
    if not updated:
        raise HTTPException(status_code=409, detail='Session is not heartbeat-eligible')
    return SessionHeartbeatResponse(id=updated.id, state=updated.state, last_heartbeat_at=updated.last_heartbeat_at, updated_at=updated.updated_at)


@router.post('/sessions/{id}/reconnect', response_model=SessionHeartbeatResponse)
def session_reconnect(id: int, token: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = SessionService(db)
    row = svc.get_session_for_user(id, user)
    if not row:
        raise HTTPException(status_code=404, detail='Session not found')
    updated = svc.reconnect(id, token)
    if not updated:
        raise HTTPException(status_code=409, detail='Reconnect failed')
    return SessionHeartbeatResponse(id=updated.id, state=updated.state, last_heartbeat_at=updated.last_heartbeat_at, updated_at=updated.updated_at)
