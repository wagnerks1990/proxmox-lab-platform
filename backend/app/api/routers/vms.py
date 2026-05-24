import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.services.rbac import get_role_name
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import StudentVM, User, VMTemplate, AuditLog, ProxmoxCluster, ProxmoxClusterDefault, ProxmoxNode
from app.schemas.vm import VMResponse, VMCreateResponse, CreateVMRequest
from app.services.proxmox import ProxmoxClient
from app.services.placement import choose_cluster_node, PlacementError
from app.services.proxmox_bootstrap import ProxmoxBootstrapService
from app.architecture.events import bus, DomainEvent, VM_STARTED

router = APIRouter()


def _get_vm_for_user(db: Session, user: User, vm_id: int):
    q = db.query(StudentVM).filter(StudentVM.id == vm_id)
    if get_role_name(user) == 'Student':
        q = q.filter(StudentVM.owner_id == user.id)
    vm = q.first()
    if not vm:
        raise HTTPException(status_code=404, detail='VM not found')
    return vm


@router.get('/vms', response_model=list[VMResponse])
async def list_vms(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(StudentVM)
    if get_role_name(user) == 'Student':
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
    if not template:
        raise HTTPException(status_code=404, detail='Template not found')

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

        try:
            decision = choose_cluster_node(node_dicts, running_counts, placement_policy, default_node, allowed_nodes=allowed_nodes)
        except PlacementError as exc:
            raise HTTPException(status_code=409, detail={'error': str(exc)})

        selected_node = decision.selected_node
        placement_reason = decision.reason

    vmid = 200000 + user.id * 100 + db.query(StudentVM).count() + 1
    vm_name = f"{user.username}-{vmid}"

    vm = StudentVM(owner_id=user.id, template_id=template.id, vm_name=vm_name, vmid=vmid, proxmox_node=selected_node, status='provisioning', operating_system='linux', access_protocols='novnc,ssh,spice')
    db.add(vm)
    db.flush()

    proxmox = ProxmoxClient()
    message = f'VM created. Placement: {placement_reason} ({selected_node})'
    try:
        resp = await proxmox.clone_vm(template.proxmox_node, template.source_vmid, vmid, vm_name)
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

    db.add(AuditLog(actor_id=user.id, action='vm.create.placement', target_type='student_vm', target_id=str(vm.id)))
    db.commit(); db.refresh(vm)
    return VMCreateResponse(**vm.__dict__, message=message)


@router.post('/vms/{id}/start', response_model=VMResponse)
async def start_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    await ProxmoxClient().start_vm(vm.proxmox_node, vm.vmid)
    vm.status = (await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid)).get('status', vm.status)
    db.commit(); db.refresh(vm)
    bus.publish(DomainEvent(name=VM_STARTED, payload={'vm_id': vm.id, 'actor_id': user.id}))
    return vm


@router.post('/vms/{id}/stop', response_model=VMResponse)
async def stop_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    await ProxmoxClient().stop_vm(vm.proxmox_node, vm.vmid)
    vm.status = (await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid)).get('status', vm.status)
    db.commit(); db.refresh(vm)
    return vm


@router.post('/vms/{id}/reboot', response_model=VMResponse)
async def reboot_vm(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    await ProxmoxClient().reboot_vm(vm.proxmox_node, vm.vmid)
    vm.status = (await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid)).get('status', vm.status)
    db.commit(); db.refresh(vm)
    return vm


@router.get('/vms/{id}/status', response_model=VMResponse)
async def refresh_vm_status(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    try:
        vm.status = (await ProxmoxClient().get_vm_status(vm.proxmox_node, vm.vmid)).get('status', vm.status)
    except Exception:
        vm.status = 'missing' if vm.status not in {'error', 'missing'} else vm.status
    db.commit(); db.refresh(vm)
    return vm


@router.delete('/vms/{id}', response_model=dict)
async def delete_vm_record(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vm = _get_vm_for_user(db, user, id)
    db.delete(vm)
    db.commit()
    return {'ok': True, 'message': 'App VM record removed.'}


@router.delete('/admin/lab-vms/{id}/app-record', response_model=dict)
async def delete_app_record_admin(id: int, force: bool = False, _user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if get_role_name(_user) != 'Admin':
        raise HTTPException(status_code=403, detail='Admin access required')
    vm = db.query(StudentVM).filter(StudentVM.id == id).first()
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
