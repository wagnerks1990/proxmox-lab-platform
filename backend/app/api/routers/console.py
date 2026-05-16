from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import User, StudentVM
from app.schemas.console import ConsoleLaunchResponse
from app.services.console_service import ConsoleService
from app.services.proxmox import ProxmoxClient

router = APIRouter()


def _get_vm_for_user(db: Session, user: User, vm_id: int):
    q = db.query(StudentVM).filter(StudentVM.id == vm_id)
    if user.role.name == 'Student':
        q = q.filter(StudentVM.owner_id == user.id)
    vm = q.first()
    if not vm:
        raise HTTPException(status_code=404, detail='VM not found')
    return vm


@router.get('/vms/{id}/console/terminal-url', response_model=ConsoleLaunchResponse)
async def console_terminal_url(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    return await ConsoleService(db).terminal_url(user, vm)


@router.get('/vms/{id}/console/rdp', response_model=ConsoleLaunchResponse)
async def console_rdp(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    host = vm.assigned_ip or vm.hostname or vm.vm_name
    return {'type': 'rdp', 'host': host, 'rdp_file': f'full address:s:{host}\nusername:s:{vm.default_username or "student"}\nprompt for credentials:i:1\n'}


@router.get('/vms/{id}/console/spice', response_model=ConsoleLaunchResponse)
async def console_spice(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    cfg = await ProxmoxClient().get_spice_config(vm.proxmox_node, vm.vmid)
    return {'type': 'spice', 'url': str(cfg)}


@router.get('/vms/{id}/console/novnc', response_model=ConsoleLaunchResponse)
async def console_novnc(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    t = await ProxmoxClient().get_novnc_ticket(vm.proxmox_node, vm.vmid)
    port=t.get('port'); ticket=t.get('ticket')
    novnc_url=f"/api/vms/{vm.id}/console/novnc/view?port={port}&ticket={ticket}"
    return {'type': 'novnc', 'ticket': ticket, 'port': port, 'vmid': vm.vmid, 'node': vm.proxmox_node, 'novnc_url': novnc_url}
