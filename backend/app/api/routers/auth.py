from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.services.rbac import get_role_name
from app.db.session import get_db
from app.models.models import AuthSession
from app.schemas.auth import LoginRequest, PasswordChangeRequest, SessionResponse, TokenResponse, UserResponse
from app.api.deps import get_authenticated_user, get_current_auth_session
from app.services.audit_service import record_audit_event
from app.services.auth_service import change_password, login_user, revoke_session

router = APIRouter()


@router.post('/auth/login', response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else None
    return TokenResponse(access_token=login_user(
        db,
        data.username,
        data.password,
        client_ip=client_ip,
        user_agent=request.headers.get('user-agent'),
        request_id=getattr(request.state, 'request_id', None),
    ))


@router.get('/auth/me', response_model=UserResponse)
def me(user=Depends(get_authenticated_user)):
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=get_role_name(user),
        role_id=getattr(user, 'role_id', None),
        is_active=getattr(user, 'is_active', True),
        force_password_change=getattr(user, 'force_password_change', False),
    )


@router.post('/auth/change-password', response_model=TokenResponse)
def update_password(data: PasswordChangeRequest, user=Depends(get_authenticated_user), db: Session = Depends(get_db)):
    return TokenResponse(access_token=change_password(db, user, data.current_password, data.new_password))


@router.post('/auth/logout', status_code=204)
def logout(session: AuthSession = Depends(get_current_auth_session), db: Session = Depends(get_db)):
    revoke_session(db, session, reason='logout')
    record_audit_event(db, actor_id=session.user_id, action='identity.logout', target_type='auth_session', target_id=str(session.id))
    db.commit()


@router.get('/auth/sessions', response_model=list[SessionResponse])
def sessions(current: AuthSession = Depends(get_current_auth_session), user=Depends(get_authenticated_user), db: Session = Depends(get_db)):
    rows = db.query(AuthSession).filter(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)).order_by(AuthSession.created_at.desc()).all()
    return [SessionResponse(
        id=row.id,
        current=row.id == current.id,
        client_ip=row.client_ip,
        user_agent=row.user_agent,
        created_at=row.created_at.isoformat() if row.created_at else None,
        expires_at=row.expires_at.isoformat() if row.expires_at else None,
    ) for row in rows]


@router.delete('/auth/sessions/{session_id}', status_code=204)
def remove_session(session_id: int, current: AuthSession = Depends(get_current_auth_session), user=Depends(get_authenticated_user), db: Session = Depends(get_db)):
    row = db.query(AuthSession).filter(AuthSession.id == session_id, AuthSession.user_id == user.id).first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail='Session not found')
    revoke_session(db, row, reason='user_revoked')
    record_audit_event(db, actor_id=user.id, action='identity.session_revoked', target_type='auth_session', target_id=str(row.id), metadata={'current_session': row.id == current.id})
    db.commit()
