from fastapi import APIRouter, Depends, HTTPException, WebSocket
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.services.rbac import get_role_name
from app.db.session import get_db
from app.core.config import settings
from app.models.models import StudentVM, User
from app.services.console_ws_service import ConsoleWsService
from app.services.organization_access import OrganizationContext, organization_role_at_least, resolve_organization_context

router = APIRouter()


def _get_user_from_ws_token(db: Session, token: str | None):
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username = payload.get('sub')
    except JWTError:
        return None
    user = db.query(User).filter(User.username == username).first()
    if not user or not getattr(user, 'is_active', True) or not get_role_name(user):
        return None
    return user


def _get_vm_for_user(db: Session, user: User, vm_id: int, organization: OrganizationContext):
    q = db.query(StudentVM).filter(StudentVM.id == vm_id, StudentVM.organization_id == organization.id)
    if organization.role == 'student':
        q = q.filter(StudentVM.owner_id == user.id)
    elif not organization_role_at_least(organization, 'instructor'):
        return None
    return q.first()


@router.websocket('/vms/{id}/console/ssh/ws')
async def ssh_ws(id: int, websocket: WebSocket, db: Session = Depends(get_db)):
    user = _get_user_from_ws_token(db, websocket.query_params.get('token'))
    if not user:
        await websocket.close(code=1008, reason='Invalid token'); return
    requested = websocket.query_params.get('organization_id')
    try:
        organization = resolve_organization_context(db, user, int(requested) if requested else None)
    except (ValueError, HTTPException):
        await websocket.close(code=1008, reason='Invalid organization'); return
    vm = _get_vm_for_user(db, user, id, organization)
    if not vm:
        await websocket.close(code=1008, reason='Forbidden'); return
    await ConsoleWsService(db).ssh_ws(websocket, user, vm)


@router.websocket('/vms/{id}/console/novnc/ws')
async def novnc_ws(id: int, websocket: WebSocket, db: Session = Depends(get_db)):
    user = _get_user_from_ws_token(db, websocket.query_params.get('token'))
    if not user:
        await websocket.close(code=1008, reason='Invalid token'); return
    requested = websocket.query_params.get('organization_id')
    try:
        organization = resolve_organization_context(db, user, int(requested) if requested else None)
    except (ValueError, HTTPException):
        await websocket.close(code=1008, reason='Invalid organization'); return
    vm = _get_vm_for_user(db, user, id, organization)
    if not vm:
        await websocket.close(code=1008, reason='Forbidden'); return
    await ConsoleWsService(db).novnc_ws(websocket, user, vm)
