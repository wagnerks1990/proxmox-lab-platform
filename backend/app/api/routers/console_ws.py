from fastapi import APIRouter, Depends, HTTPException, WebSocket
from sqlalchemy.orm import Session

from app.api.deps import get_user_from_token
from app.db.session import get_db
from app.models.models import StudentVM, User
from app.services.console_ws_service import ConsoleWsService
from app.services.organization_access import OrganizationContext, organization_role_at_least, resolve_organization_context
from app.services.classroom_access import enforce_student_vm_operation

router = APIRouter()


def _get_user_from_ws_token(db: Session, token: str | None):
    if not token:
        return None
    try:
        user = get_user_from_token(token, db)
    except HTTPException:
        return None
    if getattr(user, 'force_password_change', False):
        return None
    return user


def _get_vm_for_user(db: Session, user: User, vm_id: int, organization: OrganizationContext, operation: str):
    q = db.query(StudentVM).filter(StudentVM.id == vm_id, StudentVM.organization_id == organization.id)
    if organization.role == 'student':
        q = q.filter(StudentVM.owner_id == user.id)
    elif not organization_role_at_least(organization, 'instructor'):
        return None
    vm = q.first()
    if vm and organization.role == 'student':
        try:
            enforce_student_vm_operation(db, user_id=user.id, organization_id=organization.id, vm=vm, operation=operation)
        except HTTPException:
            return None
    return vm


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
    vm = _get_vm_for_user(db, user, id, organization, 'terminal')
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
    vm = _get_vm_for_user(db, user, id, organization, 'console')
    if not vm:
        await websocket.close(code=1008, reason='Forbidden'); return
    await ConsoleWsService(db).novnc_ws(websocket, user, vm)
