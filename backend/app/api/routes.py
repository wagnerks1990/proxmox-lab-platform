from time import time
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import httpx
import asyncssh
import asyncio
import websockets
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import User, VMTemplate, Permission, StudentVM, AuditLog, ConnectionLaunch
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.schemas.vm import TemplateResponse, CreateVMRequest, VMResponse, VMCreateResponse, AuditLogResponse, TemplateCreateRequest, TemplateUpdateRequest, ConnectionLaunchResponse
from app.services.security import verify_password, create_access_token
from app.services.proxmox import ProxmoxClient
from app.api.deps import get_current_user, require_role
from jose import jwt, JWTError
from app.core.config import settings
from app.architecture.events import bus, DomainEvent, VM_STARTED, VM_STOPPED, VM_REBOOTED, VM_DELETED, SESSION_CREATED, TASK_FAILED, GUEST_AGENT_DISCOVERED
from app.architecture.policies import can_launch_vm, can_view_audit_logs, PolicyError
from app.architecture.idempotency import store as idempotency_store
from app.api.routers.console import router as console_router
from app.api.routers.sessions import router as sessions_router

router = APIRouter(prefix='/api')
MAX_VMS_PER_USER = 5
MAX_RUNNING_VMS_PER_USER = 3
CONSOLE_RATE_LIMIT = {}


def _proxmox_error(exc: Exception):
    if isinstance(exc, httpx.HTTPStatusError):
        return HTTPException(status_code=502, detail={'error': 'Proxmox API error', 'status_code': exc.response.status_code, 'body': exc.response.text})
    if isinstance(exc, TimeoutError):
        return HTTPException(status_code=504, detail={'error': str(exc)})
    return HTTPException(status_code=502, detail={'error': str(exc)})


def _get_vm_for_user(db: Session, user: User, vm_id: int):
    q = db.query(StudentVM).filter(StudentVM.id == vm_id)
    if user.role.name == 'Student':
        q = q.filter(StudentVM.owner_id == user.id)
    vm = q.first()
    if not vm:
        raise HTTPException(status_code=404, detail='VM not found')
    return vm


def _ensure_quota(db: Session, user: User):
    owned = db.query(StudentVM).filter(StudentVM.owner_id == user.id)
    if owned.count() >= MAX_VMS_PER_USER:
        raise HTTPException(status_code=409, detail={'error': 'Quota exceeded', 'code': 'max_vms', 'max_vms_per_user': MAX_VMS_PER_USER})
    if owned.filter(StudentVM.status == 'running').count() >= MAX_RUNNING_VMS_PER_USER:
        raise HTTPException(status_code=409, detail={'error': 'Quota exceeded', 'code': 'max_running_vms', 'max_running_vms_per_user': MAX_RUNNING_VMS_PER_USER})




def _get_user_from_ws_token(db: Session, token: str | None):
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username = payload.get('sub')
    except JWTError:
        return None
    return db.query(User).filter(User.username == username).first()


def _discover_vm_ip(interfaces):
    for iface in interfaces:
        for addr in iface.get('ip-addresses', []):
            if addr.get('ip-address-type') == 'ipv4' and not addr.get('ip-address', '').startswith('127.'):
                return addr.get('ip-address')
    return None

def _rate_limit(user: User, vmid: int, action: str):
    key = f'{user.id}:{vmid}:{action}'
    now = time()
    last = CONSOLE_RATE_LIMIT.get(key, 0)
    if now - last < 3:
        raise HTTPException(status_code=429, detail={'error': 'Too many console launches. Please retry shortly.'})
    CONSOLE_RATE_LIMIT[key] = now


def _log_connection_launch(db: Session, user: User, vm: StudentVM, protocol: str, status: str = 'success', details: str | None = None):
    db.add(ConnectionLaunch(actor_id=user.id, vm_id=vm.id, protocol=protocol, status=status, details=details))


@router.get('/health')
async def health(db: Session = Depends(get_db)):
    db_ok = True
    pmx_ok = True
    db_error = None
    pmx_error = None
    try:
        db.execute(text('SELECT 1'))
    except Exception as exc:
        db_ok = False
        db_error = str(exc)
    try:
        await ProxmoxClient().list_nodes()
    except Exception as exc:
        pmx_ok = False
        pmx_error = str(exc)
    return {'backend': 'ok', 'database': {'ok': db_ok, 'error': db_error}, 'proxmox': {'ok': pmx_ok, 'error': pmx_error}}

@router.post('/auth/login', response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    return TokenResponse(access_token=create_access_token(user.username))

@router.get('/auth/me', response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, username=user.username, email=user.email, role=user.role.name)

@router.get('/templates', response_model=list[TemplateResponse])
def templates(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role.name in ['Teacher', 'Admin']:
        return db.query(VMTemplate).all()
    return db.query(VMTemplate).join(Permission, Permission.template_id == VMTemplate.id).filter(Permission.user_id == user.id, VMTemplate.enabled.is_(True)).all()

@router.get('/vms', response_model=list[VMResponse])
async def list_vms(user: User = Depends(get_current_user), db: Session = Depends(get_db), username: str | None = None, status: str | None = None, template: int | None = None, node: str | None = None):
    q = db.query(StudentVM)
    if user.role.name == 'Student':
        q = q.filter(StudentVM.owner_id == user.id)
    else:
        if username:
            q = q.join(User, User.id == StudentVM.owner_id).filter(User.username == username)
        if status:
            q = q.filter(StudentVM.status == status)
        if template:
            q = q.filter(StudentVM.template_id == template)
        if node:
            q = q.filter(StudentVM.proxmox_node == node)
    rows = q.all()
    proxmox = ProxmoxClient()
    for vm in rows:
        try:
            data = await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)
            vm.status = data.get('status', vm.status)
            vm.hostname = data.get('name', vm.hostname)
            vm.assigned_ip = vm.assigned_ip
        except Exception:
            vm.status = vm.status or 'error'
    db.commit()
    return rows

@router.get('/vms/{id}/network')
async def vm_network(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    proxmox = ProxmoxClient()
    try:
        status = await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)
        interfaces = await proxmox.get_guest_network(vm.proxmox_node, vm.vmid)
    except Exception as exc:
        raise _proxmox_error(exc)
    ip = None
    for iface in interfaces:
        for addr in iface.get('ip-addresses', []):
            if addr.get('ip-address-type') == 'ipv4' and not addr.get('ip-address', '').startswith('127.'):
                ip = addr.get('ip-address')
                break
        if ip:
            break
    vm.assigned_ip = ip
    vm.hostname = status.get('name', vm.hostname)
    db.add(AuditLog(actor_id=user.id, action='network_vm', target_type='student_vm', target_id=str(vm.vmid)))
    db.commit(); db.refresh(vm)
    return {'id': vm.id, 'status': status.get('status'), 'uptime': status.get('uptime'), 'hostname': vm.hostname, 'assigned_ip': vm.assigned_ip, 'interfaces': interfaces}

# keep prior endpoints below
@router.post('/vms', response_model=VMCreateResponse)
async def create_vm(payload: CreateVMRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    template = db.query(VMTemplate).filter(VMTemplate.id == payload.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail='Template not found')
    if user.role.name == 'Student':
        allowed = db.query(Permission).filter(Permission.user_id == user.id, Permission.template_id == payload.template_id).first()
        if not allowed or not template.enabled:
            raise HTTPException(status_code=403, detail='Template not allowed')
        _ensure_quota(db, user)
    if db.query(StudentVM).filter(StudentVM.owner_id == user.id, StudentVM.status == 'provisioning').first():
        raise HTTPException(status_code=409, detail={'error': 'Creation already in progress', 'code': 'vm_creation_in_progress'})
    vmid = 200000 + user.id * 100 + db.query(StudentVM).count() + 1
    vm_name = f"{user.username}-{''.join(ch for ch in payload.lab_name.lower() if ch.isalnum() or ch == '-')[:20]}-{vmid}"
    vm = StudentVM(owner_id=user.id, template_id=template.id, vm_name=vm_name, vmid=vmid, proxmox_node=template.proxmox_node, status='provisioning', operating_system='linux', access_protocols='novnc,ssh,spice')
    db.add(vm); db.flush()
    proxmox = ProxmoxClient(); message = 'VM created.'
    try:
        resp = await proxmox.clone_vm(template.proxmox_node, template.source_vmid, vmid, vm_name)
        upid = resp.get('data')
        if upid:
            task = await proxmox.wait_for_task(template.proxmox_node, upid)
            if task.get('exitstatus') not in ['OK', None]:
                vm.status = 'error'; db.commit(); raise HTTPException(status_code=502, detail={'error': 'Clone task failed', 'upid': upid, 'exitstatus': task.get('exitstatus')})
        vm.status = 'stopped'
        if payload.auto_start:
            try:
                await proxmox.start_vm(template.proxmox_node, vmid)
                live = await proxmox.get_vm_status(template.proxmox_node, vmid)
                vm.status = live.get('status', 'stopped')
            except Exception as start_exc:
                vm.status = 'stopped'; message = f'VM cloned successfully but auto-start failed: {start_exc}'
    except HTTPException:
        raise
    except Exception as exc:
        vm.status = 'error'; db.commit(); raise _proxmox_error(exc)
    db.add(AuditLog(actor_id=user.id, action='create_vm', target_type='student_vm', target_id=str(vmid))); db.commit(); db.refresh(vm)
    return VMCreateResponse(**vm.__dict__, message=message)

@router.post('/vms/{id}/start', response_model=VMResponse)
async def start_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id); await ProxmoxClient().start_vm(vm.proxmox_node, vm.vmid); vm.status = (await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid)).get('status', vm.status); db.commit(); db.refresh(vm); bus.publish(DomainEvent(name=VM_STARTED, payload={'vm_id': vm.id, 'actor_id': user.id})); return vm
@router.post('/vms/{id}/stop', response_model=VMResponse)
async def stop_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id); await ProxmoxClient().stop_vm(vm.proxmox_node, vm.vmid); vm.status = (await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid)).get('status', vm.status); db.commit(); db.refresh(vm); bus.publish(DomainEvent(name=VM_STOPPED, payload={'vm_id': vm.id, 'actor_id': user.id})); return vm
@router.post('/vms/{id}/reboot', response_model=VMResponse)
async def reboot_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id); await ProxmoxClient().reboot_vm(vm.proxmox_node, vm.vmid); vm.status = (await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid)).get('status', vm.status); db.commit(); db.refresh(vm); bus.publish(DomainEvent(name=VM_REBOOTED, payload={'vm_id': vm.id, 'actor_id': user.id})); return vm
@router.delete('/vms/{id}')
async def delete_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id); await ProxmoxClient().delete_vm(vm.proxmox_node, vm.vmid); vm_id = vm.id; db.delete(vm); db.commit(); bus.publish(DomainEvent(name=VM_DELETED, payload={'vm_id': vm_id, 'actor_id': user.id})); return {'ok': True}
@router.get('/vms/{id}/status')
async def vm_status(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id); status = await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid); vm.status = status.get('status', vm.status); db.commit(); db.refresh(vm); return {'id': vm.id, 'vmid': vm.vmid, 'status': vm.status, 'node': vm.proxmox_node}
@router.get('/admin/audit-logs', response_model=list[AuditLogResponse])
def audit_logs(user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    try:
        can_view_audit_logs(user)
    except PolicyError as exc:
        raise HTTPException(status_code=403, detail={'error': str(exc)})
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()

@router.get('/admin/templates', response_model=list[TemplateResponse])
def admin_templates(user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    return db.query(VMTemplate).all()
@router.post('/admin/templates', response_model=TemplateResponse)
def create_template(payload: TemplateCreateRequest, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    t = VMTemplate(**payload.model_dump()); db.add(t); db.commit(); db.refresh(t); return t
@router.patch('/admin/templates/{id}', response_model=TemplateResponse)
def patch_template(id: int, payload: TemplateUpdateRequest, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    t = db.query(VMTemplate).filter(VMTemplate.id == id).first();
    if not t: raise HTTPException(status_code=404, detail='Template not found')
    for k, v in payload.model_dump(exclude_none=True).items(): setattr(t, k, v)
    db.commit(); db.refresh(t); return t
@router.delete('/admin/templates/{id}')
def remove_template(id: int, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    t = db.query(VMTemplate).filter(VMTemplate.id == id).first();
    if not t: raise HTTPException(status_code=404, detail='Template not found')
    db.delete(t); db.commit(); return JSONResponse({'ok': True})


@router.websocket('/vms/{id}/console/ssh/ws')
async def ssh_ws(id: int, websocket: WebSocket, db: Session = Depends(get_db)):
    token = websocket.query_params.get('token')
    user = _get_user_from_ws_token(db, token)
    if not user:
        await websocket.close(code=1008, reason='Invalid token')
        return
    try:
        vm = _get_vm_for_user(db, user, id)
    except HTTPException:
        await websocket.close(code=1008, reason='Forbidden')
        return

    host = vm.assigned_ip
    if not host:
        try:
            interfaces = await ProxmoxClient().get_guest_network(vm.proxmox_node, vm.vmid)
            host = _discover_vm_ip(interfaces)
            if host:
                vm.assigned_ip = host
                db.commit()
        except Exception:
            pass

    if not host:
        await websocket.accept()
        await websocket.send_text('ERROR: No VM IP address found. Install/enable QEMU guest agent or manually set assigned_ip.')
        await websocket.close(code=1000)
        return

    username = vm.ssh_username or settings.lab_vm_ssh_username or vm.default_username or 'student'
    password = settings.lab_vm_ssh_password
    port = vm.ssh_port or 22
    if not password:
        await websocket.accept()
        await websocket.send_text('ERROR: LAB_VM_SSH_PASSWORD is not configured on backend.')
        await websocket.close(code=1000)
        return

    await websocket.accept()
    db.add(AuditLog(actor_id=user.id, action='ssh_ws_launch', target_type='student_vm', target_id=str(vm.vmid))); db.commit()

    try:
        async with asyncssh.connect(host, port=port, username=username, password=password, known_hosts=None) as conn:
            process = await conn.create_process(term_type='xterm', term_size=(24, 120))

            async def to_ws():
                try:
                    while not process.stdout.at_eof():
                        chunk = await process.stdout.read(1024)
                        if chunk:
                            await websocket.send_text(chunk)
                        else:
                            break
                except Exception:
                    return

            async def from_ws():
                while True:
                    msg = await websocket.receive_text()
                    process.stdin.write(msg)

            import asyncio
            sender = asyncio.create_task(to_ws())
            receiver = asyncio.create_task(from_ws())
            done, pending = await asyncio.wait({sender, receiver}, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.send_text(f'ERROR: SSH connection failed: {exc}')
        await websocket.close(code=1011)


@router.websocket('/vms/{id}/console/novnc/ws')
async def console_novnc_ws(id: int, websocket: WebSocket, db: Session = Depends(get_db)):
    token = websocket.query_params.get('token')
    user = _get_user_from_ws_token(db, token)
    if not user:
        await websocket.close(code=1008, reason='Invalid token')
        return
    try:
        vm = _get_vm_for_user(db, user, id)
    except HTTPException:
        await websocket.close(code=1008, reason='Forbidden')
        return
    if not vm.console_enabled:
        await websocket.close(code=1008, reason='Console disabled for VM')
        return
    try:
        ticket_data = await ProxmoxClient().get_novnc_ticket(vm.proxmox_node, vm.vmid)
        port = ticket_data.get('port')
        ticket = ticket_data.get('ticket')
        if not port or not ticket:
            raise HTTPException(status_code=502, detail={'error': 'Failed to get noVNC ticket'})
        await websocket.accept()
        db.add(AuditLog(actor_id=user.id, action='novnc_ws_launch', target_type='student_vm', target_id=str(vm.vmid))); db.commit()
        path = f"/api2/json/nodes/{vm.proxmox_node}/qemu/{vm.vmid}/vncwebsocket?port={port}&vncticket={ticket}"
        base = settings.proxmox_base_url.replace('/api2/json', '')
        ws_url = base.replace('https://', 'wss://').replace('http://', 'ws://') + path
        async with websockets.connect(ws_url, ssl=settings.proxmox_verify_ssl) as pmx:
            async def c2p():
                while True:
                    data = await websocket.receive_text()
                    await pmx.send(data)
            async def p2c():
                while True:
                    data = await pmx.recv()
                    await websocket.send_text(data if isinstance(data, str) else data.decode('utf-8', 'ignore'))
            t1 = asyncio.create_task(c2p())
            t2 = asyncio.create_task(p2c())
            done, pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
    except WebSocketDisconnect:
        return
    except Exception as exc:
        try:
            await websocket.send_text(f'ERROR: noVNC proxy failed: {exc}')
            await websocket.close(code=1011)
        except Exception:
            return


@router.get('/vms/{id}/console/novnc/view')
async def console_novnc_view(id: int, port: int, ticket: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    base = settings.proxmox_base_url.replace('/api2/json', '')
    novnc = f"{base}/?console=kvm&novnc=1&vmid={vm.vmid}&node={vm.proxmox_node}&vncticket={ticket}&port={port}"
    return {'url': novnc}


router.include_router(console_router)
router.include_router(sessions_router)
