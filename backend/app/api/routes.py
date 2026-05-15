from fastapi import APIRouter, Depends, HTTPException
import httpx
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import User, VMTemplate, Permission, StudentVM, AuditLog
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.schemas.vm import TemplateResponse, CreateVMRequest, VMResponse
from app.services.security import verify_password, create_access_token
from app.services.proxmox import ProxmoxClient
from app.api.deps import get_current_user

router = APIRouter(prefix='/api')


def _proxmox_error(exc: Exception):
    if isinstance(exc, httpx.HTTPStatusError):
        detail = {'error': 'Proxmox API error', 'status_code': exc.response.status_code, 'body': exc.response.text}
        return HTTPException(status_code=502, detail=detail)
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
        rows = db.query(VMTemplate).all()
    else:
        rows = db.query(VMTemplate).join(Permission, Permission.template_id == VMTemplate.id).filter(Permission.user_id == user.id).all()
    return rows


@router.get('/vms', response_model=list[VMResponse])
async def list_vms(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(StudentVM)
    if user.role.name == 'Student':
        q = q.filter(StudentVM.owner_id == user.id)
    rows = q.all()
    proxmox = ProxmoxClient()
    for vm in rows:
        try:
            status = await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)
            vm.status = status.get('status', vm.status)
        except Exception:
            pass
    db.commit()
    return rows


@router.post('/vms', response_model=VMResponse)
async def create_vm(payload: CreateVMRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    template = db.query(VMTemplate).filter(VMTemplate.id == payload.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail='Template not found')
    if user.role.name == 'Student':
        allowed = db.query(Permission).filter(Permission.user_id == user.id, Permission.template_id == payload.template_id).first()
        if not allowed:
            raise HTTPException(status_code=403, detail='Template not allowed')

    vmid = 200000 + user.id * 100 + db.query(StudentVM).count() + 1
    safe_lab = ''.join(ch for ch in payload.lab_name.lower() if ch.isalnum() or ch == '-')[:20]
    vm_name = f'{user.username}-{safe_lab}-{vmid}'

    proxmox = ProxmoxClient()
    try:
        clone_response = await proxmox.clone_vm(template.proxmox_node, template.source_vmid, vmid, vm_name)
        upid = clone_response.get('data')
        if upid:
            await proxmox.wait_for_task(template.proxmox_node, upid)
        if payload.auto_start:
            await proxmox.start_vm(template.proxmox_node, vmid)
    except Exception as exc:
        raise _proxmox_error(exc)

    vm = StudentVM(owner_id=user.id, template_id=template.id, vm_name=vm_name, vmid=vmid, proxmox_node=template.proxmox_node, status='running' if payload.auto_start else 'stopped')
    db.add(vm)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action='create_vm', target_type='student_vm', target_id=str(vmid)))
    db.commit()
    db.refresh(vm)
    return vm


@router.post('/vms/{id}/start', response_model=VMResponse)
async def start_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    try:
        await ProxmoxClient().start_vm(vm.proxmox_node, vm.vmid)
    except Exception as exc:
        raise _proxmox_error(exc)
    vm.status = 'running'
    db.add(AuditLog(actor_id=user.id, action='start_vm', target_type='student_vm', target_id=str(vm.vmid)))
    db.commit(); db.refresh(vm)
    return vm


@router.post('/vms/{id}/stop', response_model=VMResponse)
async def stop_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    try:
        await ProxmoxClient().stop_vm(vm.proxmox_node, vm.vmid)
    except Exception as exc:
        raise _proxmox_error(exc)
    vm.status = 'stopped'
    db.add(AuditLog(actor_id=user.id, action='stop_vm', target_type='student_vm', target_id=str(vm.vmid)))
    db.commit(); db.refresh(vm)
    return vm


@router.post('/vms/{id}/reboot', response_model=VMResponse)
async def reboot_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    try:
        await ProxmoxClient().reboot_vm(vm.proxmox_node, vm.vmid)
    except Exception as exc:
        raise _proxmox_error(exc)
    vm.status = 'running'
    db.add(AuditLog(actor_id=user.id, action='reboot_vm', target_type='student_vm', target_id=str(vm.vmid)))
    db.commit(); db.refresh(vm)
    return vm


@router.delete('/vms/{id}')
async def delete_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    try:
        await ProxmoxClient().delete_vm(vm.proxmox_node, vm.vmid)
    except Exception as exc:
        raise _proxmox_error(exc)
    db.add(AuditLog(actor_id=user.id, action='delete_vm', target_type='student_vm', target_id=str(vm.vmid)))
    db.delete(vm)
    db.commit()
    return {'ok': True}


@router.get('/vms/{id}/status')
async def vm_status(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    try:
        status = await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid)
    except Exception as exc:
        raise _proxmox_error(exc)
    vm.status = status.get('status', vm.status)
    db.add(AuditLog(actor_id=user.id, action='status_vm', target_type='student_vm', target_id=str(vm.vmid)))
    db.commit(); db.refresh(vm)
    return {'id': vm.id, 'vmid': vm.vmid, 'status': vm.status, 'node': vm.proxmox_node}
