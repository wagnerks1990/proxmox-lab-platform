from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import User, StudentVM
from app.schemas.console import ConsoleLaunchResponse
from app.services.console_service import ConsoleService
from app.services.organization_access import (
    OrganizationContext,
    get_current_organization,
    organization_role_at_least,
)
from app.services.classroom_access import enforce_student_vm_operation

router = APIRouter()


def _get_vm_for_user(
    db: Session,
    user: User,
    vm_id: int,
    organization: OrganizationContext,
    operation: str,
):
    q = db.query(StudentVM).filter(
        StudentVM.id == vm_id,
        StudentVM.organization_id == organization.id,
        StudentVM.deleted_at.is_(None),
    )
    if organization.role == "student":
        q = q.filter(StudentVM.owner_id == user.id)
    elif not organization_role_at_least(organization, "instructor"):
        raise HTTPException(status_code=403, detail="A valid role is required")
    vm = q.first()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    if organization.role == "student":
        enforce_student_vm_operation(
            db,
            user_id=user.id,
            organization_id=organization.id,
            vm=vm,
            operation=operation,
        )
    return vm


@router.get("/vms/{id}/console/terminal-url", response_model=ConsoleLaunchResponse)
async def console_terminal_url(
    id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    organization: OrganizationContext = Depends(get_current_organization),
):
    vm = _get_vm_for_user(db, user, id, organization, "terminal")
    return await ConsoleService(db).terminal_url(user, vm)


@router.get("/vms/{id}/console/rdp", response_model=ConsoleLaunchResponse)
async def console_rdp(
    id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    organization: OrganizationContext = Depends(get_current_organization),
):
    vm = _get_vm_for_user(db, user, id, organization, "rdp")
    host = vm.assigned_ip or vm.hostname or vm.vm_name
    return {
        "type": "rdp",
        "host": host,
        "rdp_file": f"full address:s:{host}\nusername:s:{vm.default_username or 'student'}\nprompt for credentials:i:1\n",
    }


@router.get("/vms/{id}/console/spice", response_model=ConsoleLaunchResponse)
async def console_spice(
    id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    organization: OrganizationContext = Depends(get_current_organization),
):
    raise HTTPException(status_code=501, detail="SPICE console is not supported")


@router.get("/vms/{id}/console/novnc", response_model=ConsoleLaunchResponse)
async def console_novnc(
    id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    organization: OrganizationContext = Depends(get_current_organization),
):
    vm = _get_vm_for_user(db, user, id, organization, "console")
    return {
        "type": "novnc",
        "vmid": vm.vmid,
        "node": vm.proxmox_node,
        "launch_url": f"/console/{vm.id}",
    }
