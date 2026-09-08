import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import (
    AuditLog,
    LabAssignment,
    ProxmoxCluster,
    ProxmoxClusterDefault,
    ProxmoxNode,
    StudentVM,
    User,
    VMTemplate,
)
from app.schemas.vm import VMResponse, VMCreateResponse, CreateVMRequest
from app.services.proxmox import ProxmoxClient
from app.services.placement import choose_cluster_node, PlacementError
from app.services.proxmox_bootstrap import ProxmoxBootstrapService
from app.architecture.events import bus, DomainEvent, VM_STARTED
from app.services.organization_access import OrganizationContext, enforce_organization_role, get_current_organization, organization_role_at_least
from app.services.classroom_access import active_assignment_for_vm, assignment_for_provisioning, enforce_student_vm_operation

router = APIRouter()


def _get_vm_for_user(db: Session, user: User, vm_id: int, organization: OrganizationContext, operation: str = 'view'):
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


@router.get('/vms', response_model=list[VMResponse])
async def list_vms(user: User = Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    q = db.query(StudentVM).filter(StudentVM.organization_id == organization.id)
    if organization.role == 'student':
        q = q.filter(StudentVM.owner_id == user.id)
    elif not organization_role_at_least(organization, 'instructor'):
        raise HTTPException(status_code=403, detail='A valid role is required')
    rows = q.all()
    if organization.role == 'student':
        visible = []
        for vm in rows:
            access = active_assignment_for_vm(db, user_id=user.id, organization_id=organization.id, vm_id=vm.id)
            if not access:
                continue
            assignment, _run, lab = access
            vm.allowed_stop = lab.student_can_power_off
            vm.allowed_delete = False
            vm.allowed_terminal = lab.terminal_enabled
            vm.allowed_console = lab.console_enabled
            vm.allowed_rdp = lab.rdp_enabled
            vm.allowed_spice = lab.console_enabled
            vm.assignment_expires_at = assignment.expires_at
            visible.append(vm)
        rows = visible
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
async def create_vm(payload: CreateVMRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    template = db.query(VMTemplate).filter(VMTemplate.id == payload.template_id, VMTemplate.organization_id == organization.id).first()
    if not template:
        raise HTTPException(status_code=404, detail='Template not found')
    if not template.enabled:
        raise HTTPException(status_code=409, detail='Template is disabled')

    assignment = None
    if organization.role == 'student':
        assignment, _run = assignment_for_provisioning(
            db,
            assignment_id=payload.assignment_id,
            user_id=user.id,
            organization_id=organization.id,
            template_id=template.id,
        )
    elif not organization_role_at_least(organization, 'instructor'):
        raise HTTPException(status_code=403, detail='A valid role is required')

    selected_node = template.proxmox_node
    placement_reason = 'template default node'

    active_cluster = db.query(ProxmoxCluster).filter(ProxmoxCluster.is_active.is_(True)).first()
    if active_cluster:
        defaults = db.query(ProxmoxClusterDefault).filter(ProxmoxClusterDefault.cluster_id == active_cluster.id).first()
        placement_policy = getattr(defaults, 'placement_policy', None) or (
            'prefer_default_then_balance' if getattr(defaults, 'default_node', None) else 'balanced'
        )
        default_node = getattr(defaults, 'default_node', None)
        default_storage = getattr(defaults, 'default_storage', None)
        default_bridge = getattr(defaults, 'default_bridge', None)

        nodes = db.query(ProxmoxNode).filter(ProxmoxNode.cluster_id == active_cluster.id).all()
        node_dicts = [{'node_name': n.node_name, 'status': n.status, 'memory_total': n.memory_total, 'memory_used': n.memory_used, 'cpu_total': n.cpu_total, 'cpu_used': n.cpu_used} for n in nodes]
        running_counts = {n.node_name: db.query(StudentVM).filter(StudentVM.proxmox_node == n.node_name, StudentVM.status == 'running').count() for n in nodes}

        svc = ProxmoxBootstrapService(db)
        templates = await svc.discover_templates(active_cluster)
        template_nodes = {str(t.get('node')) for t in templates if t.get('vmid') == template.source_vmid and t.get('node')}
        if not template_nodes:
            raise HTTPException(status_code=409, detail={'error': f'Template VMID {template.source_vmid} was not found on any online node.'})

        if default_storage:
            storage_rows = await svc.discover_storage(active_cluster)
            storage_nodes = {str(s.get('node')) for s in storage_rows if s.get('storage') == default_storage and str(s.get('active')).lower() not in {'0', 'false', 'none'}}
            allowed_nodes = template_nodes & storage_nodes
            if not allowed_nodes:
                raise HTTPException(status_code=409, detail={'error': 'No online Proxmox node has the requested storage/template combination.'})
        else:
            allowed_nodes = template_nodes
        if default_bridge:
            network_rows = await svc.discover_networks(active_cluster)
            bridge_nodes = {str(n.get('node')) for n in network_rows if n.get('bridge') == default_bridge}
            allowed_nodes = allowed_nodes & bridge_nodes
            if not allowed_nodes:
                raise HTTPException(status_code=409, detail={'error': f'No eligible node has required bridge {default_bridge} for template placement.'})

        try:
            decision = choose_cluster_node(node_dicts, running_counts, placement_policy, default_node, allowed_nodes=allowed_nodes)
        except PlacementError as exc:
            raise HTTPException(status_code=409, detail={'error': str(exc)})

        selected_node = decision.selected_node
        placement_reason = decision.reason

    vmid = 200000 + user.id * 100 + db.query(StudentVM).count() + 1
    vm_name = f"{user.username}-{vmid}"

    vm = StudentVM(organization_id=organization.id, owner_id=user.id, template_id=template.id, vm_name=vm_name, vmid=vmid, proxmox_node=selected_node, status='provisioning', operating_system='linux', access_protocols='novnc,ssh,spice')
    db.add(vm)
    db.flush()

    proxmox = ProxmoxClient()
    message = f'VM created. Placement: {placement_reason} ({selected_node})'
    try:
        # source template can be on one node while target placement can be another eligible node
        resp = await proxmox.clone_vm(selected_node, template.source_vmid, vmid, vm_name)
        upid = resp.get('data')
        if upid:
            task = await proxmox.wait_for_task(template.proxmox_node, upid)
            if task.get('exitstatus') not in ['OK', None]:
                vm.status = 'error'
                db.commit()
                raise HTTPException(status_code=502, detail={'success': False, 'error': 'Clone task failed', 'exitstatus': task.get('exitstatus'), 'proxmox_node': selected_node, 'requested_vmid': vmid, 'selected_template': template.source_vmid, 'placement_reason': placement_reason})

        try:
            live = await proxmox.get_vm_status(selected_node, vmid)
            vm.status = live.get('status', 'stopped')
        except Exception:
            vm.status = 'missing'
            db.commit()
            raise HTTPException(status_code=502, detail={'success': False, 'error': 'Clone completed but VM not found on selected node', 'proxmox_node': selected_node, 'requested_vmid': vmid, 'selected_template': template.source_vmid, 'placement_reason': placement_reason})

        if payload.auto_start and vm.status != 'running':
            try:
                await proxmox.start_vm(selected_node, vmid)
                live = await proxmox.get_vm_status(selected_node, vmid)
                vm.status = live.get('status', vm.status)
            except Exception as start_exc:
                message = f'VM cloned successfully but auto-start failed: {start_exc}'

    except HTTPException:
        raise
    except Exception as exc:
        vm.status = 'error'
        db.commit()
        raise HTTPException(status_code=502, detail={'success': False, 'error': str(exc), 'proxmox_node': selected_node, 'requested_vmid': vmid, 'selected_template': template.source_vmid, 'placement_reason': placement_reason})

    db.add(AuditLog(organization_id=organization.id, actor_id=user.id, action='vm.create.placement', target_type='student_vm', target_id=str(vm.id)))
    if assignment:
        assignment.student_vm_id = vm.id
        assignment.status = 'ready'
    db.commit(); db.refresh(vm)
    return VMCreateResponse(**vm.__dict__, message=message)


@router.post('/vms/{id}/start', response_model=VMResponse)
async def start_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    vm = _get_vm_for_user(db, user, id, organization, 'start')
    await ProxmoxClient().start_vm(vm.proxmox_node, vm.vmid)
    vm.status = (await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid)).get('status', vm.status)
    db.add(AuditLog(organization_id=organization.id, actor_id=user.id, action='vm.start', target_type='student_vm', target_id=str(vm.id)))
    db.commit(); db.refresh(vm)
    bus.publish(DomainEvent(name=VM_STARTED, payload={'organization_id': organization.id, 'vm_id': vm.id, 'actor_id': user.id}))
    return vm


@router.post('/vms/{id}/stop', response_model=VMResponse)
async def stop_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    vm = _get_vm_for_user(db, user, id, organization, 'stop')
    await ProxmoxClient().stop_vm(vm.proxmox_node, vm.vmid)
    vm.status = (await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid)).get('status', vm.status)
    db.add(AuditLog(organization_id=organization.id, actor_id=user.id, action='vm.stop', target_type='student_vm', target_id=str(vm.id)))
    db.commit(); db.refresh(vm)
    return vm


@router.post('/vms/{id}/reboot', response_model=VMResponse)
async def reboot_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    vm = _get_vm_for_user(db, user, id, organization, 'reboot')
    await ProxmoxClient().reboot_vm(vm.proxmox_node, vm.vmid)
    vm.status = (await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid)).get('status', vm.status)
    db.add(AuditLog(organization_id=organization.id, actor_id=user.id, action='vm.reboot', target_type='student_vm', target_id=str(vm.id)))
    db.commit(); db.refresh(vm)
    return vm


@router.get('/vms/{id}/status', response_model=VMResponse)
async def refresh_vm_status(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    vm = _get_vm_for_user(db, user, id, organization, 'view')
    try:
        vm.status = (await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid)).get('status', vm.status)
    except Exception:
        vm.status = 'missing' if vm.status not in {'error', 'missing'} else vm.status
    db.commit(); db.refresh(vm)
    return vm


@router.delete('/vms/{id}', response_model=dict)
async def delete_vm_record(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    vm = _get_vm_for_user(db, user, id, organization, 'delete')
    assignment = db.query(LabAssignment).filter(LabAssignment.student_vm_id == vm.id).first()
    if assignment:
        assignment.student_vm_id = None
        if assignment.status == 'ready':
            assignment.status = 'assigned'
    db.delete(vm)
    db.commit()
    return {'ok': True, 'message': 'App VM record removed.'}


@router.delete('/admin/lab-vms/{id}/app-record', response_model=dict)
async def delete_app_record_admin(id: int, force: bool = False, _user: User = Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    enforce_organization_role(organization, 'admin')
    vm = db.query(StudentVM).filter(StudentVM.id == id, StudentVM.organization_id == organization.id).first()
    if not vm:
        raise HTTPException(status_code=404, detail='App VM record not found')

    if vm.status not in {'missing', 'error'}:
        try:
            await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid)
            if not force:
                raise HTTPException(status_code=409, detail='VM exists in Proxmox; refusing to remove app record without force=true')
        except HTTPException:
            raise
        except Exception as exc:
            err = str(exc).lower()
            # Allow delete if VM is effectively not found in Proxmox; otherwise surface an integration error.
            if not any(x in err for x in ['not found', 'does not exist', '404']):
                raise HTTPException(status_code=502, detail='Unable to verify Proxmox VM state; refusing app-record delete until Proxmox check succeeds')

    db.add(AuditLog(organization_id=organization.id, actor_id=_user.id, action='vm.app_record.delete', target_type='student_vm', target_id=str(vm.id)))
    assignment = db.query(LabAssignment).filter(LabAssignment.student_vm_id == vm.id).first()
    if assignment:
        assignment.student_vm_id = None
        if assignment.status == 'ready':
            assignment.status = 'assigned'
    db.delete(vm)
    db.commit()
    return {
        'ok': True,
        'deleted': True,
        'deleted_app_vm_id': id,
        'vmid': vm.vmid,
        'deleted_record_only': True,
        'proxmox_vm_deleted': False,
        'message': 'Removed app VM record only. No Proxmox VM was deleted.',
    }
