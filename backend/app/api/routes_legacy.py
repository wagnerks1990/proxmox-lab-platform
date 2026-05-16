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
from app.models.models import User, VMTemplate, Permission, StudentVM, AuditLog, ConnectionLaunch, VMPool, LabGroup, LabGroupMember, ProtocolSettings, ProxmoxCluster, ProxmoxNode, DesktopPool
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.schemas.vm import TemplateResponse, CreateVMRequest, VMResponse, VMCreateResponse, AuditLogResponse, TemplateCreateRequest, TemplateUpdateRequest, ConnectionLaunchResponse, PoolBase, PoolResponse, GroupResponse, GroupCreateRequest, GroupUpdateRequest, GroupMemberRequest, ProtocolSettingsResponse, ProxmoxClusterBase, ProxmoxClusterResponse, ProxmoxNodeBase, ProxmoxNodeResponse, DesktopPoolBase, DesktopPoolResponse
from app.services.security import verify_password, create_access_token
from app.services.proxmox import ProxmoxClient
from app.services.protocol import ProtocolService
from app.services.connection_broker import get_guacamole_launch
from app.services.guacamole import check_guacamole_reachable
from app.api.deps import get_current_user, require_role
from jose import jwt, JWTError
from app.core.config import settings

router = APIRouter(prefix='/api')
MAX_VMS_PER_USER = 5
MAX_RUNNING_VMS_PER_USER = 3
CONSOLE_RATE_LIMIT = {}


def _role_name(user: User) -> str:
    return (getattr(getattr(user, 'role_rel', None), 'name', None) or getattr(user, 'role', None) or '').strip()


def _proxmox_error(exc: Exception):
    if isinstance(exc, httpx.HTTPStatusError):
        return HTTPException(status_code=502, detail={'error': 'Proxmox API error', 'status_code': exc.response.status_code, 'body': exc.response.text})
    if isinstance(exc, TimeoutError):
        return HTTPException(status_code=504, detail={'error': str(exc)})
    return HTTPException(status_code=502, detail={'error': str(exc)})


def _get_vm_for_user(db: Session, user: User, vm_id: int):
    q = db.query(StudentVM).filter(StudentVM.id == vm_id)
    if _role_name(user) == 'Student':
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

def _select_pool_node(db: Session, pool: VMPool | None):
    if not pool:
        return None
    strategy = (pool.placement_strategy or 'any_enabled_node').lower()
    nodes_q = db.query(ProxmoxNode).filter(ProxmoxNode.enabled.is_(True))
    if pool.cluster_id:
        nodes_q = nodes_q.filter(ProxmoxNode.cluster_id == pool.cluster_id)
    nodes = nodes_q.all()
    if strategy == 'fixed_node' and pool.preferred_node_id:
        return db.query(ProxmoxNode).filter(ProxmoxNode.id == pool.preferred_node_id, ProxmoxNode.enabled.is_(True)).first()
    if strategy == 'least_running_vms':
        best = None; best_cnt = 10**9
        for n in nodes:
            c = db.query(StudentVM).filter(StudentVM.proxmox_node == n.node_name, StudentVM.status == 'running').count()
            if c < best_cnt:
                best_cnt = c; best = n
        return best
    if strategy == 'round_robin' and nodes:
        idx = (db.query(StudentVM).count()) % len(nodes)
        return nodes[idx]
    if strategy == 'least_memory_usage':
        return sorted(nodes, key=lambda x: float((x.memory_usage or '0').split('%')[0] or 0))[0] if nodes else None
    return nodes[0] if nodes else None


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
    return UserResponse(id=user.id, username=user.username, email=user.email, role=_role_name(user).lower())

@router.get('/templates', response_model=list[TemplateResponse])
def templates(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if _role_name(user) in ['Teacher', 'Admin']:
        return db.query(VMTemplate).all()
    return db.query(VMTemplate).join(Permission, Permission.template_id == VMTemplate.id).filter(Permission.user_id == user.id, VMTemplate.enabled.is_(True)).all()

@router.get('/vms', response_model=list[VMResponse])
async def list_vms(user: User = Depends(get_current_user), db: Session = Depends(get_db), username: str | None = None, status: str | None = None, template: int | None = None, node: str | None = None):
    q = db.query(StudentVM)
    if _role_name(user) == 'Student':
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

@router.get('/vms/{id}/console/novnc')
async def console_novnc(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    _rate_limit(user, vm.vmid, 'novnc')
    try:
        return await ProtocolService(db).novnc_ticket_scaffold(user, vm)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        raise _proxmox_error(exc)

@router.get('/vms/{id}/console/spice')
async def console_spice(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    _rate_limit(user, vm.vmid, 'spice')
    try:
        cfg = await ProxmoxClient().get_spice_config(vm.proxmox_node, vm.vmid)
    except Exception as exc:
        msg = str(exc).lower()
        if 'spice' in msg and ('not enabled' in msg or 'no spice' in msg or 'port' in msg):
            raise HTTPException(status_code=400, detail={'error': 'SPICE is not enabled for this VM.'})
        raise _proxmox_error(exc)
    db.add(AuditLog(actor_id=user.id, action='console_spice', target_type='student_vm', target_id=str(vm.vmid))); db.commit()
    return {'type': 'spice', 'config': cfg}

@router.get('/vms/{id}/console/ssh')
async def console_ssh(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    _rate_limit(user, vm.vmid, 'ssh')
    db.add(AuditLog(actor_id=user.id, action='console_ssh', target_type='student_vm', target_id=str(vm.vmid))); db.commit()
    host = vm.assigned_ip or vm.hostname or vm.vm_name
    return {'type': 'ssh', 'host': host, 'username': vm.default_username or 'student', 'web_terminal_url': f'/api/vms/{vm.id}/console/ssh'}



@router.get('/vms/{id}/console/terminal-url')
async def console_terminal_url(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    _rate_limit(user, vm.vmid, 'web_terminal')
    return await ProtocolService(db).web_terminal_url(user, vm)



@router.get('/vms/{id}/console/guacamole')
async def console_guacamole(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db), protocol: str = 'rdp'):
    vm = _get_vm_for_user(db, user, id)
    _rate_limit(user, vm.vmid, 'guacamole')
    if protocol not in ['rdp', 'vnc', 'ssh']:
        raise HTTPException(status_code=400, detail={'error': 'Unsupported Guacamole protocol'})
    db.add(AuditLog(actor_id=user.id, action='console_guacamole', target_type='student_vm', target_id=str(vm.vmid)))
    _log_connection_launch(db, user, vm, 'GUACAMOLE', 'pending', f'protocol={protocol}')
    db.commit()
    reachable, err = await check_guacamole_reachable()
    return get_guacamole_launch(vm.vmid, protocol, reachable=reachable)

@router.get('/vms/{id}/console/rdp')
async def console_rdp(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    _rate_limit(user, vm.vmid, 'rdp')
    db.add(AuditLog(actor_id=user.id, action='console_rdp', target_type='student_vm', target_id=str(vm.vmid))); db.commit()
    host = vm.assigned_ip or vm.hostname or vm.vm_name
    rdp_text = f'full address:s:{host}\nusername:s:{vm.default_username or "student"}\nprompt for credentials:i:1\n'
    return {'type': 'rdp', 'host': host, 'rdp_file': rdp_text}

# keep prior endpoints below
@router.post('/vms', response_model=VMCreateResponse)
async def create_vm(payload: CreateVMRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    template = db.query(VMTemplate).filter(VMTemplate.id == payload.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail='Template not found')
    if _role_name(user) == 'Student':
        allowed = db.query(Permission).filter(Permission.user_id == user.id, Permission.template_id == payload.template_id).first()
        if not allowed or not template.enabled:
            raise HTTPException(status_code=403, detail='Template not allowed')
        _ensure_quota(db, user)
    if db.query(StudentVM).filter(StudentVM.owner_id == user.id, StudentVM.status == 'provisioning').first():
        raise HTTPException(status_code=409, detail={'error': 'Creation already in progress', 'code': 'vm_creation_in_progress'})
    vmid = 200000 + user.id * 100 + db.query(StudentVM).count() + 1
    vm_name = f"{user.username}-{''.join(ch for ch in payload.lab_name.lower() if ch.isalnum() or ch == '-')[:20]}-{vmid}"
    selected_node = template.proxmox_node
    pool = db.query(VMPool).filter(VMPool.enabled.is_(True)).first()
    if pool:
        if db.query(StudentVM).filter(StudentVM.proxmox_node == (pool.node_id or selected_node)).count() >= (pool.max_vms or 999999):
            raise HTTPException(status_code=409, detail={'error':'Quota exceeded','code':'max_vms_per_pool'})
        node_obj = _select_pool_node(db, pool)
        if not node_obj:
            raise HTTPException(status_code=409, detail={'error':'No eligible node found for pool placement'})
        selected_node = node_obj.node_name
    vm = StudentVM(owner_id=user.id, template_id=template.id, vm_name=vm_name, vmid=vmid, proxmox_node=selected_node, status='provisioning', operating_system='linux', access_protocols='novnc,ssh,spice')
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
    vm = _get_vm_for_user(db, user, id); await ProxmoxClient().start_vm(vm.proxmox_node, vm.vmid); vm.status = (await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid)).get('status', vm.status); db.commit(); db.refresh(vm); return vm
@router.post('/vms/{id}/stop', response_model=VMResponse)
async def stop_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id); await ProxmoxClient().stop_vm(vm.proxmox_node, vm.vmid); vm.status = (await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid)).get('status', vm.status); db.commit(); db.refresh(vm); return vm
@router.post('/vms/{id}/reboot', response_model=VMResponse)
async def reboot_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id); await ProxmoxClient().reboot_vm(vm.proxmox_node, vm.vmid); vm.status = (await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid)).get('status', vm.status); db.commit(); db.refresh(vm); return vm
@router.delete('/vms/{id}')
async def delete_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id); await ProxmoxClient().delete_vm(vm.proxmox_node, vm.vmid); db.delete(vm); db.commit(); return {'ok': True}
@router.get('/vms/{id}/status')
async def vm_status(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id); status = await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid); vm.status = status.get('status', vm.status); db.commit(); db.refresh(vm); return {'id': vm.id, 'vmid': vm.vmid, 'status': vm.status, 'node': vm.proxmox_node}
@router.get('/admin/audit-logs', response_model=list[AuditLogResponse])
def audit_logs(user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()
@router.get('/admin/session-activity', response_model=list[ConnectionLaunchResponse])
def session_activity(user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), protocol: str | None = None, status: str | None = None, username: str | None = None, date_from: str | None = None, date_to: str | None = None):
    q = db.query(ConnectionLaunch, User.username, StudentVM.vm_name).outerjoin(User, User.id == ConnectionLaunch.actor_id).outerjoin(StudentVM, StudentVM.id == ConnectionLaunch.vm_id)
    if protocol:
        q = q.filter(ConnectionLaunch.protocol == protocol)
    if status:
        q = q.filter(ConnectionLaunch.status == status)
    if username:
        q = q.filter(User.username.ilike(f'%{username}%'))
    rows = q.order_by(ConnectionLaunch.created_at.desc()).limit(500).all()
    if not rows:
        return []
    out = []
    for x in rows:
        cl = x.ConnectionLaunch
        uname = x.username or 'unknown'
        vmn = x.vm_name or 'unknown'
        out.append({
            'id': cl.id,
            'actor_id': cl.actor_id or 0,
            'vm_id': cl.vm_id or 0,
            'protocol': cl.protocol or 'unknown',
            'status': cl.status or 'unknown',
            'details': f"user={uname}; vm={vmn}; {cl.details or ''}",
            'created_at': cl.created_at,
        })
    return out

@router.get('/admin/templates', response_model=list[TemplateResponse])
def admin_templates(user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    return db.query(VMTemplate).all()
@router.post('/admin/templates', response_model=TemplateResponse)
def create_template(payload: TemplateCreateRequest, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    allowed = {'name','proxmox_node','source_vmid','operating_system','default_protocol','default_protocols','description','cluster_id','node_id','storage_pool','network_bridge','spice_enabled','rdp_enabled','web_terminal_enabled','is_active','enabled'}
    data = {k:v for k,v in payload.model_dump().items() if k in allowed}
    try:
        t = VMTemplate(**data)
    except TypeError as exc:
        raise HTTPException(status_code=400, detail={'error': f'Invalid template payload: {exc}'})
    db.add(t); db.commit(); db.refresh(t); return t
@router.patch('/admin/templates/{id}', response_model=TemplateResponse)
def patch_template(id: int, payload: TemplateUpdateRequest, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    t = db.query(VMTemplate).filter(VMTemplate.id == id).first();
    if not t: raise HTTPException(status_code=404, detail='Template not found')
    allowed = {'name','proxmox_node','source_vmid','operating_system','default_protocol','default_protocols','description','cluster_id','node_id','storage_pool','network_bridge','spice_enabled','rdp_enabled','web_terminal_enabled','is_active','enabled'}
    for k, v in payload.model_dump(exclude_none=True).items():
        if k in allowed: setattr(t, k, v)
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


@router.get('/admin/pools', response_model=list[PoolResponse])
def list_pools(user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    return db.query(VMPool).order_by(VMPool.created_at.desc()).all()

@router.post('/admin/pools', response_model=PoolResponse)
def create_pool(payload: PoolBase, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    p = VMPool(**payload.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    return p

@router.patch('/admin/pools/{id}', response_model=PoolResponse)
def patch_pool(id: int, payload: PoolBase, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    p = db.query(VMPool).filter(VMPool.id == id).first()
    if not p: raise HTTPException(status_code=404, detail='Pool not found')
    for k,v in payload.model_dump(exclude_none=True).items(): setattr(p,k,v)
    db.commit(); db.refresh(p); return p

@router.delete('/admin/pools/{id}')
def delete_pool(id: int, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    p = db.query(VMPool).filter(VMPool.id == id).first()
    if not p: raise HTTPException(status_code=404, detail='Pool not found')
    db.delete(p); db.commit(); return {'ok': True}

@router.get('/admin/users')
def admin_users(user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [{'id':u.id,'username':u.username,'email':u.email,'role': (_role_name(u).lower() if _role_name(u) else 'student'),'vm_count':db.query(StudentVM).filter(StudentVM.owner_id==u.id).count()} for u in users]

@router.get('/admin/groups', response_model=list[GroupResponse])
def admin_groups(user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    return db.query(LabGroup).order_by(LabGroup.created_at.desc()).all()

@router.post('/admin/groups', response_model=GroupResponse)
def create_group(payload: GroupCreateRequest, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    g = LabGroup(**payload.model_dump()); db.add(g); db.commit(); db.refresh(g); return g

@router.patch('/admin/groups/{id}', response_model=GroupResponse)
def patch_group(id: int, payload: GroupUpdateRequest, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    g = db.query(LabGroup).filter(LabGroup.id == id).first()
    if not g: raise HTTPException(status_code=404, detail='Group not found')
    for k,v in payload.model_dump(exclude_none=True).items(): setattr(g,k,v)
    db.commit(); db.refresh(g); return g

@router.post('/admin/groups/{id}/members')
def add_group_member(id: int, payload: GroupMemberRequest, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    g = db.query(LabGroup).filter(LabGroup.id==id).first()
    if not g: raise HTTPException(status_code=404, detail='Group not found')
    if not db.query(LabGroupMember).filter(LabGroupMember.group_id==id, LabGroupMember.user_id==payload.user_id).first():
        db.add(LabGroupMember(group_id=id,user_id=payload.user_id)); db.commit()
    return {'ok': True}

@router.delete('/admin/groups/{id}/members/{user_id}')
def remove_group_member(id: int, user_id: int, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    m = db.query(LabGroupMember).filter(LabGroupMember.group_id==id, LabGroupMember.user_id==user_id).first()
    if m: db.delete(m); db.commit()
    return {'ok': True}

@router.get('/admin/monitoring/summary')
async def monitoring_summary(user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    total = db.query(StudentVM).count(); running = db.query(StudentVM).filter(StudentVM.status=='running').count(); stopped = db.query(StudentVM).filter(StudentVM.status=='stopped').count()
    sessions = db.query(ConnectionLaunch).order_by(ConnectionLaunch.created_at.desc()).limit(20).all()
    failed = db.query(ConnectionLaunch).filter(ConnectionLaunch.status=='failed').count()
    db_ok=True; pmx_ok=True
    try: db.execute(text('SELECT 1'))
    except Exception: db_ok=False
    try: await ProxmoxClient().list_nodes()
    except Exception: pmx_ok=False
    node_counts = []
    for n in db.query(ProxmoxNode).all():
        vmc = db.query(StudentVM).filter(StudentVM.proxmox_node==n.node_name).count()
        rvc = db.query(StudentVM).filter(StudentVM.proxmox_node==n.node_name, StudentVM.status=='running').count()
        node_counts.append({'node':n.node_name,'cluster_id':n.cluster_id,'vm_count':vmc,'running_vm_count':rvc,'status':n.status,'cpu_usage':n.cpu_usage,'memory_usage':n.memory_usage,'storage_summary':n.storage_summary})
    cluster_health = [{'cluster':c.name,'enabled':c.enabled} for c in db.query(ProxmoxCluster).all()]
    placement_warnings = []
    if not db.query(VMPool).filter(VMPool.enabled.is_(True)).first():
        placement_warnings.append('No enabled resource pools configured')
    return {'total_vms':total,'running_vms':running,'stopped_vms':stopped,'recent_sessions':len(sessions),'failed_actions':failed,'proxmox_health':pmx_ok,'database_health':db_ok,'cluster_health':cluster_health,'node_health':node_counts,'failed_proxmox_checks':0,'placement_warnings':placement_warnings}

@router.get('/admin/settings/protocols', response_model=ProtocolSettingsResponse)
def get_protocol_settings(user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    s = db.query(ProtocolSettings).first()
    if not s:
        s = ProtocolSettings(terminal_gateway_url='http://10.0.16.162:7681')
        db.add(s); db.commit(); db.refresh(s)
    return s

@router.patch('/admin/settings/protocols', response_model=ProtocolSettingsResponse)
def patch_protocol_settings(payload: ProtocolSettingsResponse, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    s = db.query(ProtocolSettings).first()
    if not s:
        s = ProtocolSettings(); db.add(s)
    data = payload.model_dump(exclude_none=True)
    data.pop('id', None)
    for k,v in data.items(): setattr(s,k,v)
    db.commit(); db.refresh(s); return s


@router.get('/admin/proxmox/clusters', response_model=list[ProxmoxClusterResponse])
def list_clusters(user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    return db.query(ProxmoxCluster).order_by(ProxmoxCluster.created_at.desc()).all()

@router.post('/admin/proxmox/clusters', response_model=ProxmoxClusterResponse)
def create_cluster(payload: ProxmoxClusterBase, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    c = ProxmoxCluster(**payload.model_dump()); db.add(c); db.commit(); db.refresh(c); return c

@router.patch('/admin/proxmox/clusters/{id}', response_model=ProxmoxClusterResponse)
def patch_cluster(id: int, payload: ProxmoxClusterBase, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    c = db.query(ProxmoxCluster).filter(ProxmoxCluster.id==id).first()
    if not c: raise HTTPException(status_code=404, detail='Cluster not found')
    for k,v in payload.model_dump(exclude_none=True).items(): setattr(c,k,v)
    db.commit(); db.refresh(c); return c

@router.delete('/admin/proxmox/clusters/{id}')
def delete_cluster(id: int, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    c = db.query(ProxmoxCluster).filter(ProxmoxCluster.id==id).first()
    if not c: raise HTTPException(status_code=404, detail='Cluster not found')
    db.delete(c); db.commit(); return {'ok':True}

@router.get('/admin/proxmox/nodes', response_model=list[ProxmoxNodeResponse])
def list_nodes_admin(user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    return db.query(ProxmoxNode).order_by(ProxmoxNode.created_at.desc()).all()

@router.post('/admin/proxmox/nodes/sync', response_model=list[ProxmoxNodeResponse])
async def sync_nodes(user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    clusters = db.query(ProxmoxCluster).filter(ProxmoxCluster.enabled.is_(True)).all()
    for c in clusters:
        try:
            nodes = await ProxmoxClient().list_nodes()
            for n in nodes:
                name = n.get('node') or n.get('name')
                if not name: continue
                ex = db.query(ProxmoxNode).filter(ProxmoxNode.cluster_id==c.id, ProxmoxNode.node_name==name).first()
                if not ex:
                    ex = ProxmoxNode(cluster_id=c.id, node_name=name)
                    db.add(ex)
                ex.status = 'online' if n.get('status') in ['online','up',1,True] else 'unknown'
                ex.cpu_usage = str(n.get('cpu')) if n.get('cpu') is not None else ex.cpu_usage
                ex.memory_usage = str(n.get('mem')) if n.get('mem') is not None else ex.memory_usage
                ex.last_seen = func.now()
        except Exception:
            continue
    db.commit()
    return db.query(ProxmoxNode).order_by(ProxmoxNode.created_at.desc()).all()


@router.get('/admin/desktop-pools', response_model=list[DesktopPoolResponse])
def list_desktop_pools(user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    return db.query(DesktopPool).order_by(DesktopPool.created_at.desc()).all()

@router.post('/admin/desktop-pools', response_model=DesktopPoolResponse)
def create_desktop_pool(payload: DesktopPoolBase, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    p = DesktopPool(**payload.model_dump())
    db.add(p); db.commit(); db.refresh(p); return p

@router.patch('/admin/desktop-pools/{id}', response_model=DesktopPoolResponse)
def patch_desktop_pool(id: int, payload: DesktopPoolBase, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    p = db.query(DesktopPool).filter(DesktopPool.id==id).first()
    if not p: raise HTTPException(status_code=404, detail='Desktop pool not found')
    for k,v in payload.model_dump(exclude_none=True).items(): setattr(p,k,v)
    db.commit(); db.refresh(p); return p

@router.delete('/admin/desktop-pools/{id}')
def delete_desktop_pool(id: int, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    p = db.query(DesktopPool).filter(DesktopPool.id==id).first()
    if not p: raise HTTPException(status_code=404, detail='Desktop pool not found')
    db.delete(p); db.commit(); return {'ok':True}

@router.patch('/admin/proxmox/nodes/{id}/enabled')
def toggle_node_enabled(id: int, enabled: bool, user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    n = db.query(ProxmoxNode).filter(ProxmoxNode.id==id).first()
    if not n: raise HTTPException(status_code=404, detail='Node not found')
    n.enabled = enabled; db.commit(); db.refresh(n); return n

@router.get('/admin/proxmox/clusters/summary')
def cluster_summary(user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    out=[]
    for c in db.query(ProxmoxCluster).all():
        node_count = db.query(ProxmoxNode).filter(ProxmoxNode.cluster_id==c.id).count()
        vm_count = db.query(StudentVM).join(ProxmoxNode, ProxmoxNode.node_name==StudentVM.proxmox_node, isouter=True).filter(ProxmoxNode.cluster_id==c.id).count()
        out.append({'cluster_id':c.id,'name':c.name,'enabled':c.enabled,'nodes':node_count,'vms':vm_count})
    return out

@router.get('/admin/proxmox/nodes/summary')
def node_summary(user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    out=[]
    for n in db.query(ProxmoxNode).all():
        vm_count = db.query(StudentVM).filter(StudentVM.proxmox_node==n.node_name).count()
        running = db.query(StudentVM).filter(StudentVM.proxmox_node==n.node_name, StudentVM.status=='running').count()
        out.append({'node_id':n.id,'node_name':n.node_name,'enabled':n.enabled,'status':n.status,'vm_count':vm_count,'running_vm_count':running,'eligible':bool(n.enabled)})
    return out

@router.get('/admin/schema-health')
def schema_health(user: User = Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    from sqlalchemy import inspect
    ins = inspect(db.bind)
    required = {
        'users': ['id','username','email','role_id'],
        'roles': ['id','name'],
        'student_vms': ['id','owner_id','vmid','proxmox_node','status'],
        'vm_templates': ['id','name','proxmox_node','source_vmid'],
        'vm_pools': ['id','name'],
        'connection_launches': ['id','actor_id','vm_id','protocol','status','created_at'],
        'proxmox_clusters': ['id','name','api_url'],
        'proxmox_nodes': ['id','cluster_id','node_name'],
        'desktop_pools': ['id','name','template_id','resource_pool_id'],
    }
    missing_tables=[]; missing_columns=[]; warnings=[]
    for t, cols in required.items():
        if not ins.has_table(t):
            missing_tables.append(t); continue
        existing={c['name'] for c in ins.get_columns(t)}
        for c in cols:
            if c not in existing: missing_columns.append(f'{t}.{c}')
    if db.query(ConnectionLaunch).count()==0: warnings.append('No session activity records yet')
    return {'ok': not missing_tables and not missing_columns, 'missing_tables': missing_tables, 'missing_columns': missing_columns, 'warnings': warnings}


@router.get('/admin/guacamole/status')
async def guacamole_status(user: User = Depends(require_role('Teacher', 'Admin'))):
    reachable, error = await check_guacamole_reachable()
    return {
        'reachable': reachable,
        'internal_url': settings.guacamole_internal_url,
        'base_url': settings.guacamole_base_url,
        'error': error,
        'guidance': None if reachable else 'Verify local Guacamole at GUACAMOLE_INTERNAL_URL and nginx proxy for /guacamole',
    }
