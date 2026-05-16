import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import StudentVM, User, VMTemplate, Permission, AuditLog
from app.schemas.vm import VMResponse, VMCreateResponse, CreateVMRequest
from app.services.proxmox import ProxmoxClient
from app.architecture.events import bus, DomainEvent, VM_STARTED, VM_STOPPED, VM_REBOOTED, VM_DELETED

router = APIRouter()


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


@router.get('/vms', response_model=list[VMResponse])
async def list_vms(user: User = Depends(get_current_user), db: Session = Depends(get_db), username: str | None = None, status: str | None = None, template: int | None = None, node: str | None = None):
    q = db.query(StudentVM)
    if user.role.name == 'Student':
        q = q.filter(StudentVM.owner_id == user.id)
    rows = q.all()
    proxmox = ProxmoxClient()
    for vm in rows:
        try:
            data = await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)
            vm.status = data.get('status', vm.status)
        except Exception:
            vm.status = vm.status or 'error'
    db.commit()
    return rows

@router.post('/vms', response_model=VMCreateResponse)
async def create_vm(payload: CreateVMRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    template = db.query(VMTemplate).filter(VMTemplate.id == payload.template_id).first()
    if not template: raise HTTPException(status_code=404, detail='Template not found')
    vmid = 200000 + user.id * 100 + db.query(StudentVM).count() + 1
    vm_name = f"{user.username}-{vmid}"
    vm = StudentVM(owner_id=user.id, template_id=template.id, vm_name=vm_name, vmid=vmid, proxmox_node=template.proxmox_node, status='provisioning', operating_system='linux', access_protocols='novnc,ssh,spice')
    db.add(vm); db.flush(); db.commit(); db.refresh(vm)
    return VMCreateResponse(**vm.__dict__, message='VM created.')

@router.post('/vms/{id}/start', response_model=VMResponse)
async def start_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id); await ProxmoxClient().start_vm(vm.proxmox_node, vm.vmid); vm.status = (await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid)).get('status', vm.status); db.commit(); db.refresh(vm); bus.publish(DomainEvent(name=VM_STARTED, payload={'vm_id': vm.id, 'actor_id': user.id})); return vm
