from fastapi import APIRouter, Depends, WebSocket
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.models.models import StudentVM, User
from app.services.console_ws_service import ConsoleWsService

router = APIRouter()


def _get_user_from_ws_token(db: Session, token: str | None):
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username = payload.get('sub')
    except JWTError:
        return None
    return db.query(User).filter(User.username == username).first()


def _get_vm_for_user(db: Session, user: User, vm_id: int):
    q = db.query(StudentVM).filter(StudentVM.id == vm_id)
    if user.role.name == 'Student':
        q = q.filter(StudentVM.owner_id == user.id)
    return q.first()


@router.websocket('/vms/{id}/console/ssh/ws')
async def ssh_ws(id: int, websocket: WebSocket, db: Session = Depends(get_db)):
    user = _get_user_from_ws_token(db, websocket.query_params.get('token'))
    if not user:
        await websocket.close(code=1008, reason='Invalid token'); return
    vm = _get_vm_for_user(db, user, id)
    if not vm:
        await websocket.close(code=1008, reason='Forbidden'); return
    await ConsoleWsService(db).ssh_ws(websocket, user, vm)


@router.websocket('/vms/{id}/console/novnc/ws')
async def novnc_ws(id: int, websocket: WebSocket, db: Session = Depends(get_db)):
    user = _get_user_from_ws_token(db, websocket.query_params.get('token'))
    if not user:
        await websocket.close(code=1008, reason='Invalid token'); return
    vm = _get_vm_for_user(db, user, id)
    if not vm:
        await websocket.close(code=1008, reason='Forbidden'); return
    await ConsoleWsService(db).novnc_ws(websocket, user, vm)
