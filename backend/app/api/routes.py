from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import User, VMTemplate, Permission, StudentVM, AuditLog
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.schemas.vm import TemplateResponse, CreateVMRequest, VMResponse
from app.services.security import verify_password, create_access_token
from app.services.proxmox import ProxmoxClient
from app.api.deps import get_current_user

router = APIRouter(prefix='/api')


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


def _get_vm_for_user(vm_id: int, user: User, db: Session) -> StudentVM:
    vm = db.query(StudentVM).filter(StudentVM.id == vm_id).first()
    if not vm:
        raise HTTPException(status_code=404, detail='VM not found')
    if user.role.name == 'Student' and vm.owner_id != user.id:
        raise HTTPException(status_code=403, detail='Not allowed to manage this VM')
    return vm


def _audit(db: Session, actor_id: int, action: str, target_id: str):
    db.add(AuditLog(actor_id=actor_id, action=action, target_type='student_vm', target_id=target_id))
    db.commit()


@router.get('/vms', response_model=list[VMResponse])
async def list_vms(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(StudentVM)
    if user.role.name == 'Student':
        q = q.filter(StudentVM.owner_id == user.id)
    vms = q.all()
    proxmox = ProxmoxClient()
    for vm in vms:
        status_data = await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)
        vm.status = status_data.get('status', vm.status)
    db.commit()
    return vms


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
    upid = await proxmox.clone_vm(template.proxmox_node, template.source_vmid, vmid, vm_name)
    if isinstance(upid, str):
        await proxmox.wait_for_task(template.proxmox_node, upid)

    status = 'stopped'
    if payload.auto_start:
        await proxmox.start_vm(template.proxmox_node, vmid)
        status_data = await proxmox.get_vm_status(template.proxmox_node, vmid)
        status = status_data.get('status', 'running')

    vm = StudentVM(owner_id=user.id, template_id=template.id, vm_name=vm_name, vmid=vmid, proxmox_node=template.proxmox_node, status=status)
    db.add(vm)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action='create_vm', target_type='student_vm', target_id=str(vmid)))
    db.commit()
    db.refresh(vm)
    return vm


@router.post('/vms/{vm_id}/start')
async def start_vm(vm_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(vm_id, user, db)
    proxmox = ProxmoxClient()
    await proxmox.start_vm(vm.proxmox_node, vm.vmid)
    status_data = await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)
    vm.status = status_data.get('status', 'running')
    db.commit()
    _audit(db, user.id, 'start_vm', str(vm.vmid))
    return {'message': 'VM started', 'status': vm.status}


@router.post('/vms/{vm_id}/stop')
async def stop_vm(vm_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(vm_id, user, db)
    proxmox = ProxmoxClient()
    await proxmox.stop_vm(vm.proxmox_node, vm.vmid)
    status_data = await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)
    vm.status = status_data.get('status', 'stopped')
    db.commit()
    _audit(db, user.id, 'stop_vm', str(vm.vmid))
    return {'message': 'VM stopped', 'status': vm.status}


@router.post('/vms/{vm_id}/reboot')
async def reboot_vm(vm_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(vm_id, user, db)
    proxmox = ProxmoxClient()
    await proxmox.reboot_vm(vm.proxmox_node, vm.vmid)
    status_data = await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)
    vm.status = status_data.get('status', 'running')
    db.commit()
    _audit(db, user.id, 'reboot_vm', str(vm.vmid))
    return {'message': 'VM rebooted', 'status': vm.status}


@router.delete('/vms/{vm_id}')
async def delete_vm(vm_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(vm_id, user, db)
    proxmox = ProxmoxClient()
    await proxmox.delete_vm(vm.proxmox_node, vm.vmid)
    vmid = vm.vmid
    db.delete(vm)
    db.commit()
    _audit(db, user.id, 'delete_vm', str(vmid))
    return {'message': 'VM deleted'}


@router.get('/vms/{vm_id}/status')
async def vm_status(vm_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(vm_id, user, db)
    proxmox = ProxmoxClient()
    status_data = await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)
    vm.status = status_data.get('status', vm.status)
    db.commit()
    _audit(db, user.id, 'refresh_vm_status', str(vm.vmid))
    return {'vm_id': vm.id, 'vmid': vm.vmid, 'status': vm.status, 'raw': status_data}
