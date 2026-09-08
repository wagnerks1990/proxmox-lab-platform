from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import User, StudentVM
from app.schemas.console import ConsoleLaunchResponse
from app.services.console_service import ConsoleService
from app.services.proxmox import ProxmoxClient
from app.services.organization_access import OrganizationContext, get_current_organization, organization_role_at_least
from app.services.classroom_access import enforce_student_vm_operation

router = APIRouter()


def _get_vm_for_user(db: Session, user: User, vm_id: int, organization: OrganizationContext, operation: str):
    q = db.query(StudentVM).filter(StudentVM.id == vm_id, StudentVM.organization_id == organization.id)
    if organization.role == 'student':
        q = q.filter(StudentVM.owner_id == user.id)
    elif not organization_role_at_least(organization, 'instructor'):
        raise HTTPException(status_code=403, detail='A valid role is required')
    vm = q.first()
    if not vm:
        raise HTTPException(status_code=404, detail='VM not found')
    if organization.role == 'student':
        enforce_student_vm_operation(db, user_id=user.id, organization_id=organization.id, vm=vm, operation=operation)
    return vm


@router.get('/vms/{id}/console/terminal-url', response_model=ConsoleLaunchResponse)
async def console_terminal_url(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    vm = _get_vm_for_user(db, user, id, organization, 'terminal')
    return await ConsoleService(db).terminal_url(user, vm)


@router.get('/vms/{id}/console/rdp', response_model=ConsoleLaunchResponse)
async def console_rdp(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    vm = _get_vm_for_user(db, user, id, organization, 'rdp')
    host = vm.assigned_ip or vm.hostname or vm.vm_name
    return {'type': 'rdp', 'host': host, 'rdp_file': f'full address:s:{host}\nusername:s:{vm.default_username or "student"}\nprompt for credentials:i:1\n'}


@router.get('/vms/{id}/console/spice', response_model=ConsoleLaunchResponse)
async def console_spice(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    vm = _get_vm_for_user(db, user, id, organization, 'spice')
    cfg = await ProxmoxClient().get_spice_config(vm.proxmox_node, vm.vmid)
    return {'type': 'spice', 'url': str(cfg)}


@router.get('/vms/{id}/console/novnc', response_model=ConsoleLaunchResponse)
async def console_novnc(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    vm = _get_vm_for_user(db, user, id, organization, 'console')
    t = await ProxmoxClient().get_novnc_ticket(vm.proxmox_node, vm.vmid)
    port=t.get('port'); ticket=t.get('ticket')
    novnc_url=f"/api/vms/{vm.id}/console/novnc/view?port={port}&ticket={ticket}"
    return {'type': 'novnc', 'ticket': ticket, 'port': port, 'vmid': vm.vmid, 'node': vm.proxmox_node, 'novnc_url': novnc_url}


@router.get('/vms/{id}/console/novnc/view', response_model=ConsoleLaunchResponse)
async def console_novnc_view(id: int, port: int, ticket: str, user: User = Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    vm = _get_vm_for_user(db, user, id, organization, 'console')
    from app.core.config import settings
    base = settings.proxmox_base_url.replace('/api2/json', '')
    novnc = f"{base}/?console=kvm&novnc=1&vmid={vm.vmid}&node={vm.proxmox_node}&vncticket={ticket}&port={port}"
    return {'type': 'novnc', 'url': novnc}
