from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.models import ProxmoxCluster, ProxmoxNode, ProxmoxClusterDefault, VMTemplate, StudentVM, User
from app.services.proxmox_bootstrap import ProxmoxBootstrapService
from app.services.proxmox_resource_stats import ProxmoxResourceStatsService

router = APIRouter()


def _mask(v: str | None) -> str | None:
    if not v:
        return None
    if len(v) <= 4:
        return '****'
    return f"{v[:2]}***{v[-2:]}"


@router.get('/admin/proxmox/clusters')
def list_clusters(_user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    rows = db.query(ProxmoxCluster).order_by(ProxmoxCluster.id.desc()).all()
    return [{
        'id': r.id,
        'name': r.name,
        'api_url': r.api_url,
        'verify_ssl': r.verify_ssl,
        'auth_mode': r.auth_mode,
        'token_user': r.token_user,
        'token_id': _mask(r.token_id),
        'token_created_by_app': r.token_created_by_app,
        'is_active': r.is_active,
        'last_validated_at': r.last_validated_at,
        'last_validation_status': r.last_validation_status,
        'last_validation_error': r.last_validation_error,
    } for r in rows]


@router.post('/admin/proxmox/bootstrap-root')
async def bootstrap_root(payload: dict, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    required = ['name', 'api_url', 'root_username', 'root_password']
    missing = [k for k in required if not payload.get(k)]
    if missing:
        raise HTTPException(status_code=422, detail={'error': f'Missing fields: {", ".join(missing)}'})
    svc = ProxmoxBootstrapService(db)
    try:
        return await svc.bootstrap_with_root(payload)
    except Exception as exc:
        if str(exc) == 'TOKEN_EXISTS':
            return {
                'ok': False,
                'token_exists': True,
                'message': 'Token already exists in Proxmox for this user/token id.',
                'suggested_actions': [
                    'Choose a different token ID and retry bootstrap.',
                    'Use manual token entry with an existing token secret.',
                    'Delete/recreate token in Proxmox manually, then retry.',
                    'Delete the app cluster record if stale and re-run setup.',
                ],
            }
        raise HTTPException(status_code=400, detail={'error': str(exc)})


@router.get('/admin/proxmox/clusters/{id}')
def get_cluster(id: int, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    row = db.query(ProxmoxCluster).filter(ProxmoxCluster.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Cluster not found')
    defaults = db.query(ProxmoxClusterDefault).filter(ProxmoxClusterDefault.cluster_id == id).first()
    return {
        'id': row.id,
        'name': row.name,
        'api_url': row.api_url,
        'verify_ssl': row.verify_ssl,
        'auth_mode': row.auth_mode,
        'token_user': row.token_user,
        'token_id': _mask(row.token_id),
        'token_created_by_app': row.token_created_by_app,
        'is_active': row.is_active,
        'last_validated_at': row.last_validated_at,
        'last_validation_status': row.last_validation_status,
        'last_validation_error': row.last_validation_error,
        'defaults': {
            'default_node': getattr(defaults, 'default_node', None),
            'default_storage': getattr(defaults, 'default_storage', None),
            'default_bridge': getattr(defaults, 'default_bridge', None),
            'default_template_vmid': getattr(defaults, 'default_template_vmid', None),
            'clone_mode': getattr(defaults, 'clone_mode', None),
            'placement_policy': getattr(defaults, 'placement_policy', None),
            'notes': getattr(defaults, 'notes', None),
        },
    }


@router.patch('/admin/proxmox/clusters/{id}')
def patch_cluster(id: int, payload: dict, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    row = db.query(ProxmoxCluster).filter(ProxmoxCluster.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Cluster not found')
    for key in ['name', 'api_url', 'verify_ssl']:
        if key in payload:
            setattr(row, key, payload[key])
    db.commit()
    return {'ok': True}


@router.delete('/admin/proxmox/clusters/{id}')
def delete_cluster(id: int, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    row = db.query(ProxmoxCluster).filter(ProxmoxCluster.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Cluster not found')
    db.query(ProxmoxNode).filter(ProxmoxNode.cluster_id == id).delete()
    db.query(ProxmoxClusterDefault).filter(ProxmoxClusterDefault.cluster_id == id).delete()
    db.delete(row)
    db.commit()
    return {'ok': True, 'deleted_cluster_id': id}


@router.patch('/admin/proxmox/clusters/{id}/defaults')
def patch_defaults(id: int, payload: dict, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    row = db.query(ProxmoxCluster).filter(ProxmoxCluster.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Cluster not found')
    d = db.query(ProxmoxClusterDefault).filter(ProxmoxClusterDefault.cluster_id == id).first()
    if d is None:
        d = ProxmoxClusterDefault(cluster_id=id)
        db.add(d)
    for key in ['default_node', 'default_storage', 'default_bridge', 'default_template_vmid', 'clone_mode', 'placement_policy', 'notes']:
        if key in payload:
            setattr(d, key, payload[key])
    db.commit()
    return {
        'ok': True,
        'defaults': {
            'default_node': d.default_node,
            'default_storage': d.default_storage,
            'default_bridge': d.default_bridge,
            'default_template_vmid': d.default_template_vmid,
            'clone_mode': d.clone_mode,
            'placement_policy': d.placement_policy,
            'notes': d.notes,
        },
    }


@router.post('/admin/proxmox/clusters/{id}/activate')
def activate_cluster(id: int, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    row = db.query(ProxmoxCluster).filter(ProxmoxCluster.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Cluster not found')
    db.query(ProxmoxCluster).update({ProxmoxCluster.is_active: False})
    row.is_active = True
    row.updated_at = datetime.utcnow()
    db.commit()
    return {'ok': True, 'active_cluster_id': id}


@router.post('/admin/proxmox/clusters/{id}/validate')
async def validate_cluster(id: int, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    row = db.query(ProxmoxCluster).filter(ProxmoxCluster.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Cluster not found')
    svc = ProxmoxBootstrapService(db)
    result = await svc.validate_cluster(row)
    row.last_validated_at = datetime.utcnow()
    row.last_validation_status = 'success' if result.get('ok') else 'error'
    row.last_validation_error = None if result.get('ok') else result.get('error')
    db.commit()
    return result


@router.get('/admin/proxmox/clusters/{id}/nodes')
def list_cluster_nodes(id: int, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    return [{'id': n.id, 'node_name': n.node_name, 'status': n.status, 'last_seen_at': n.last_seen_at} for n in db.query(ProxmoxNode).filter(ProxmoxNode.cluster_id == id).all()]


@router.get('/admin/proxmox/clusters/{id}/storage')
@router.get('/admin/proxmox/cluster/{id}/storage')
@router.get('/admin/proxmox/clusters/{id}/storage/')
async def list_cluster_storage(id: int, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    row = db.query(ProxmoxCluster).filter(ProxmoxCluster.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Cluster not found')
    return await ProxmoxBootstrapService(db).discover_storage(row)


@router.get('/admin/proxmox/clusters/{id}/templates')
@router.get('/admin/proxmox/cluster/{id}/templates')
@router.get('/admin/proxmox/clusters/{id}/templates/')
async def list_cluster_templates(id: int, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    row = db.query(ProxmoxCluster).filter(ProxmoxCluster.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Cluster not found')
    return await ProxmoxBootstrapService(db).discover_templates(row)


@router.get('/admin/proxmox/clusters/{id}/networks')
@router.get('/admin/proxmox/cluster/{id}/networks')
@router.get('/admin/proxmox/clusters/{id}/networks/')
async def list_cluster_networks(id: int, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    row = db.query(ProxmoxCluster).filter(ProxmoxCluster.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Cluster not found')
    return await ProxmoxBootstrapService(db).discover_networks(row)


@router.post('/admin/proxmox/clusters/manual-token')
async def manual_token(payload: dict, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    required = ['name', 'api_url', 'token_user', 'token_id', 'token_secret']
    missing = [k for k in required if not payload.get(k)]
    if missing:
        raise HTTPException(status_code=422, detail={'error': f'Missing fields: {", ".join(missing)}'})
    svc = ProxmoxBootstrapService(db)
    result = await svc.upsert_manual_token(payload)
    if not result.get('ok'):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get('/admin/proxmox/resource-stats')
async def active_resource_stats(_user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    try:
        return await ProxmoxResourceStatsService(db).active_cluster_stats()
    except RuntimeError as exc:
        return {
            'config_source': 'not_configured',
            'cluster': {'id': None, 'name': None, 'api_url': None},
            'summary': {
                'total_nodes': 0, 'online_nodes': 0, 'offline_nodes': 0,
                'total_cpu_cores': 0, 'cpu_usage_percent': None,
                'memory_used_bytes': 0, 'memory_total_bytes': 0, 'memory_usage_percent': None,
                'disk_used_bytes': 0, 'disk_total_bytes': 0, 'disk_usage_percent': None,
                'total_vms': 0, 'running_vms': 0, 'stopped_vms': 0, 'paused_vms': 0, 'templates': 0, 'unknown_vms': 0
            },
            'nodes': [],
            'warnings': [str(exc)],
            'fetched_at': datetime.utcnow().isoformat() + 'Z',
        }


@router.get('/admin/proxmox/clusters/{id}/resource-stats')
async def cluster_resource_stats(id: int, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    row = db.query(ProxmoxCluster).filter(ProxmoxCluster.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Cluster not found')
    return await ProxmoxResourceStatsService(db).cluster_stats(row)


@router.get('/admin/proxmox/templates/discovered')
async def discovered_templates(_user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    active = db.query(ProxmoxCluster).filter(ProxmoxCluster.is_active.is_(True)).first()
    if not active:
        raise HTTPException(status_code=404, detail='No active Proxmox cluster configured')
    discovered = await ProxmoxBootstrapService(db).discover_templates(active)
    out = []
    for t in discovered:
        existing = db.query(VMTemplate).filter(VMTemplate.source_vmid == t.get('vmid')).first()
        out.append({
            'node': t.get('node'), 'vmid': t.get('vmid'), 'name': t.get('name'), 'status': t.get('status'), 'template': bool(t.get('template', True)),
            'already_imported': bool(existing), 'imported_template_id': getattr(existing, 'id', None)
        })
    return out


@router.post('/admin/proxmox/templates/import')
async def import_templates(payload: dict, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    items = payload.get('templates') if isinstance(payload.get('templates'), list) else [payload]
    imported = []
    for item in items:
        vmid = int(item['source_vmid']) if item.get('source_vmid') is not None else int(item['vmid'])
        node = item.get('proxmox_node') or item.get('node')
        name = item.get('name') or f'template-{vmid}'
        enabled = bool(item.get('enabled', True))
        row = db.query(VMTemplate).filter(VMTemplate.source_vmid == vmid).first()
        if row is None:
            row = VMTemplate(name=name, proxmox_node=node, source_vmid=vmid, enabled=enabled)
            db.add(row)
        else:
            row.name = name or row.name
            row.proxmox_node = node or row.proxmox_node
            if 'enabled' in item:
                row.enabled = enabled
        db.flush()
        imported.append({'id': row.id, 'name': row.name, 'proxmox_node': row.proxmox_node, 'source_vmid': row.source_vmid, 'enabled': row.enabled})
    db.commit()
    return {'ok': True, 'imported': imported}


@router.post('/admin/proxmox/templates/sync')
async def sync_templates(_user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    active = db.query(ProxmoxCluster).filter(ProxmoxCluster.is_active.is_(True)).first()
    if not active:
        raise HTTPException(status_code=404, detail='No active Proxmox cluster configured')
    discovered = await ProxmoxBootstrapService(db).discover_templates(active)
    imported = []
    for t in discovered:
        vmid = int(t.get('vmid'))
        row = db.query(VMTemplate).filter(VMTemplate.source_vmid == vmid).first()
        if row is None:
            row = VMTemplate(name=t.get('name') or f'template-{vmid}', proxmox_node=t.get('node'), source_vmid=vmid, enabled=True)
            db.add(row)
        else:
            row.name = t.get('name') or row.name
            row.proxmox_node = t.get('node') or row.proxmox_node
        db.flush()
        imported.append({'id': row.id, 'name': row.name, 'proxmox_node': row.proxmox_node, 'source_vmid': row.source_vmid, 'enabled': row.enabled})
    db.commit()
    return {'ok': True, 'imported_count': len(imported), 'imported': imported}


@router.get('/admin/proxmox/inventory/vms')
async def proxmox_inventory_vms(status: str | None = None, node: str | None = None, template: bool | None = None, q: str | None = None, linked: bool | None = None, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    active = db.query(ProxmoxCluster).filter(ProxmoxCluster.is_active.is_(True)).first()
    if not active:
        raise HTTPException(status_code=404, detail='No active Proxmox cluster configured')
    stats = await ProxmoxResourceStatsService(db).cluster_stats(active)
    tpl_map = {t.source_vmid: t for t in db.query(VMTemplate).all()}
    vm_map = {v.vmid: v for v in db.query(StudentVM).all()}
    users = {u.id: u.username for u in db.query(User).all()}
    items = []
    for n in stats.get('nodes', []):
        pass
    # Build from live resources for richer fields
    from app.services.proxmox import ProxmoxClient
    client = ProxmoxClient()
    import httpx
    async with httpx.AsyncClient(verify=client.verify_ssl, timeout=30, headers=client.headers) as http:
        r = await http.get(f'{client.base_url}/cluster/resources')
        r.raise_for_status()
        resources = r.json().get('data', [])
    for vm in [x for x in resources if x.get('type') == 'qemu']:
        vmid = int(vm.get('vmid'))
        is_tpl = vm.get('template') in (1, True, '1', 'true', 'True')
        linked_vm = vm_map.get(vmid)
        linked_tpl = tpl_map.get(vmid)
        row = {
            'source': 'proxmox', 'node': vm.get('node'), 'vmid': vmid, 'name': vm.get('name'), 'status': vm.get('status'), 'template': bool(is_tpl),
            'cpu_usage': vm.get('cpu'), 'memory_used': vm.get('mem'), 'memory_total': vm.get('maxmem'), 'disk_used': vm.get('disk'), 'disk_total': vm.get('maxdisk'),
            'uptime': vm.get('uptime'), 'tags': vm.get('tags'),
            'app_linked': bool(linked_vm or linked_tpl), 'app_vm_id': getattr(linked_vm, 'id', None), 'app_template_id': getattr(linked_tpl, 'id', None),
            'owner_username': users.get(linked_vm.owner_id) if linked_vm else None,
        }
        items.append(row)
    def ok(it):
        if status and (it.get('status') or '').lower() != status.lower(): return False
        if node and it.get('node') != node: return False
        if template is not None and bool(it.get('template')) != bool(template): return False
        if linked is not None and bool(it.get('app_linked')) != bool(linked): return False
        if q:
            qq=q.lower();
            if qq not in str(it.get('name','')).lower() and qq not in str(it.get('vmid','')): return False
        return True
    return [x for x in items if ok(x)]


@router.post('/admin/proxmox/vms/{node}/{vmid}/start')
async def admin_start_vm(node: str, vmid: int, _user=Depends(require_role('Admin'))):
    return await ProxmoxClient().start_vm(node, vmid)


@router.post('/admin/proxmox/vms/{node}/{vmid}/stop')
async def admin_stop_vm(node: str, vmid: int, _user=Depends(require_role('Admin'))):
    return await ProxmoxClient().stop_vm(node, vmid)


@router.post('/admin/proxmox/vms/{node}/{vmid}/reboot')
async def admin_reboot_vm(node: str, vmid: int, _user=Depends(require_role('Admin'))):
    return await ProxmoxClient().reboot_vm(node, vmid)


@router.post('/admin/proxmox/vms/{node}/{vmid}/shutdown')
async def admin_shutdown_vm(node: str, vmid: int, _user=Depends(require_role('Admin'))):
    return await ProxmoxClient()._vm_action(node, vmid, 'shutdown')


@router.get('/admin/proxmox/vms/{node}/{vmid}/status')
async def admin_vm_status(node: str, vmid: int, _user=Depends(require_role('Admin'))):
    return await ProxmoxClient().get_vm_status(node, vmid)


@router.get('/admin/proxmox/templates/availability')
async def template_availability(_user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    active = db.query(ProxmoxCluster).filter(ProxmoxCluster.is_active.is_(True)).first()
    if not active:
        raise HTTPException(status_code=404, detail='No active Proxmox cluster configured')
    svc = ProxmoxBootstrapService(db)
    discovered = await svc.discover_templates(active)
    nodes = [n.node_name for n in db.query(ProxmoxNode).filter(ProxmoxNode.cluster_id == active.id).all()]
    out = []
    by_vmid = {}
    for t in discovered:
        by_vmid.setdefault(int(t.get('vmid')), []).append(t)
    for row in db.query(VMTemplate).all():
        vmid = int(row.source_vmid)
        found = by_vmid.get(vmid, [])
        available_nodes = sorted({str(x.get('node')) for x in found if x.get('node')})
        missing_nodes = sorted([n for n in nodes if n not in available_nodes])
        warnings = [] if len(missing_nodes)==0 else [f'Only available on {", ".join(available_nodes) or "no nodes"}']
        recommended_action = (
            'Ready for balanced placement across all discovered nodes.'
            if len(missing_nodes) == 0 else
            'Use prefer_default_then_balance/manual policy, shared storage, or Proxmox-native replication before balanced placement.'
        )
        out.append({
            'template_id': row.id,
            'template_vmid': vmid,
            'name': row.name,
            'source_node': row.proxmox_node,
            'available_nodes': available_nodes,
            'missing_nodes': missing_nodes,
            'can_balance_across_all_nodes': len(missing_nodes)==0,
            'clone_target_supported': None,
            'storage_compatibility': None,
            'warnings': warnings,
            'recommended_action': recommended_action,
        })
    return out


@router.get('/admin/proxmox/reconciliation/vms')
async def reconcile_vms(_user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    inv = await proxmox_inventory_vms(_user=_user, db=db)
    inv_map = {(x.get('node'), int(x.get('vmid'))): x for x in inv}
    report = []
    matched = 0
    missing = 0
    status_updated = 0
    app_rows = db.query(StudentVM).all()
    for vm in app_rows:
        key = (vm.proxmox_node, int(vm.vmid))
        found = inv_map.get(key)
        previous_status = vm.status
        if not found:
            new_status = vm.status if vm.status in {'missing', 'error'} else 'missing'
            vm.status = new_status
            if previous_status != new_status:
                status_updated += 1
            missing += 1
            report.append({
                'app_vm_id': vm.id,
                'vmid': vm.vmid,
                'node': vm.proxmox_node,
                'state': 'app_only_missing_in_proxmox',
                'previous_status': previous_status,
                'new_status': vm.status,
                'message': f'App VM record exists but VMID {vm.vmid} was not found on {vm.proxmox_node}.',
            })
        else:
            proxmox_status = (found.get('status') or vm.status or '').lower() or vm.status
            if proxmox_status and vm.status != proxmox_status:
                vm.status = proxmox_status
                status_updated += 1
            state = 'matched' if vm.status == proxmox_status else 'status_mismatch'
            if state == 'matched':
                matched += 1
            report.append({
                'app_vm_id': vm.id,
                'vmid': vm.vmid,
                'node': vm.proxmox_node,
                'state': state,
                'previous_status': previous_status,
                'new_status': vm.status,
                'proxmox_status': proxmox_status,
                'message': f'VMID {vm.vmid} exists in Proxmox on {vm.proxmox_node}.',
            })
    db.commit()
    proxmox_only = [x for x in inv if not x.get('app_vm_id')]
    return {
        'summary': {
            'app_vms': len(app_rows),
            'matched': matched,
            'missing': missing,
            'status_updated': status_updated,
            'proxmox_only': len(proxmox_only),
        },
        'report': report,
        'proxmox_only_count': len(proxmox_only),
        'proxmox_only': proxmox_only,
    }


@router.post('/admin/proxmox/reconciliation/vms')
async def reconcile_vms_post(_user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    return await reconcile_vms(_user=_user, db=db)


@router.post('/admin/proxmox/templates/{vmid}/sync')
async def sync_template_to_nodes(vmid: int, payload: dict, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    active = db.query(ProxmoxCluster).filter(ProxmoxCluster.is_active.is_(True)).first()
    if not active:
        raise HTTPException(status_code=404, detail='No active Proxmox cluster configured')
    source_node = payload.get('source_node')
    target_nodes = payload.get('target_nodes') or []
    target_storage = payload.get('target_storage')
    if not source_node or not target_nodes:
        raise HTTPException(status_code=422, detail={'error': 'source_node and target_nodes are required'})
    # Validation-only/dry-run to avoid unsafe assumptions on cross-node template replication semantics
    svc = ProxmoxBootstrapService(db)
    storage = await svc.discover_storage(active)
    unavailable = [n for n in target_nodes if target_storage and not any(s.get('node')==n and s.get('storage')==target_storage for s in storage)]
    if unavailable:
        return {'ok': False, 'supported': False, 'message': 'Some target nodes do not have requested storage.', 'unavailable_nodes': unavailable}
    return {'ok': False, 'supported': False, 'message': 'Automated cross-node template replication is not enabled in cloud-safe mode. Use Proxmox native replication/clone workflow, then refresh discovery.'}


@router.get('/admin/proxmox/clusters/{id}/isos')
async def list_cluster_isos(id: int, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    row = db.query(ProxmoxCluster).filter(ProxmoxCluster.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Cluster not found')
    result = await ProxmoxBootstrapService(db).discover_isos(row)
    return {'items': result.get('items', []), 'warnings': result.get('warnings', [])}


@router.get('/admin/proxmox/clusters/{id}/readiness')
async def cluster_readiness(id: int, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    cluster = db.query(ProxmoxCluster).filter(ProxmoxCluster.id == id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail='Cluster not found')
    svc = ProxmoxBootstrapService(db)
    nodes = [{'node_name': n.node_name, 'status': n.status, 'memory_total': n.memory_total, 'memory_used': n.memory_used, 'cpu_total': n.cpu_total, 'cpu_used': n.cpu_used} for n in db.query(ProxmoxNode).filter(ProxmoxNode.cluster_id == id).all()]
    storage = await svc.discover_storage(cluster)
    templates = await svc.discover_templates(cluster)
    networks = await svc.discover_networks(cluster)
    isos_result = await svc.discover_isos(cluster)
    defaults = db.query(ProxmoxClusterDefault).filter(ProxmoxClusterDefault.cluster_id == id).first()
    template_vmid = getattr(defaults, 'default_template_vmid', None)
    default_storage = getattr(defaults, 'default_storage', None)
    default_bridge = getattr(defaults, 'default_bridge', None)
    policy = getattr(defaults, 'placement_policy', None)
    online_nodes = {n['node_name'] for n in nodes if (n.get('status') or '').lower() in {'online', 'up'}}
    eligible_nodes = set(online_nodes)
    warnings = list(isos_result.get('warnings', []))
    failures = []
    if not online_nodes:
        failures.append('No online nodes discovered in active cluster.')
    if template_vmid:
        tpl_nodes = {str(t.get('node')) for t in templates if int(t.get('vmid', -1)) == int(template_vmid)}
        if not tpl_nodes:
            failures.append(f'Default template VMID {template_vmid} was not found on discovered nodes.')
        elif tpl_nodes != online_nodes:
            warnings.append(f'Default template VMID {template_vmid} available only on: {", ".join(sorted(tpl_nodes))}.')
        eligible_nodes &= tpl_nodes
    if default_storage:
        st_nodes = {str(s.get('node')) for s in storage if s.get('storage') == default_storage and str(s.get('active')).lower() not in {'0', 'false', 'none'}}
        if not st_nodes:
            failures.append(f'Default storage {default_storage} not available on any discovered node.')
        eligible_nodes &= st_nodes
    if default_bridge:
        br_nodes = {str(n.get('node')) for n in networks if n.get('bridge') == default_bridge}
        if not br_nodes:
            failures.append(f'Default bridge {default_bridge} not found on discovered nodes.')
        eligible_nodes &= br_nodes
    if policy == 'balanced' and template_vmid and len(eligible_nodes) <= 1:
        warnings.append('Balanced placement is limited because template/storage/network constraints reduce eligible nodes.')
    excluded_nodes = sorted(list(online_nodes - eligible_nodes))
    excluded_reasons = {}
    for node_name in excluded_nodes:
        reasons = []
        if template_vmid:
            tpl_nodes = {str(t.get('node')) for t in templates if int(t.get('vmid', -1)) == int(template_vmid)}
            if node_name not in tpl_nodes:
                reasons.append('template_unavailable')
        if default_storage:
            st_nodes = {str(s.get('node')) for s in storage if s.get('storage') == default_storage and str(s.get('active')).lower() not in {'0', 'false', 'none'}}
            if node_name not in st_nodes:
                reasons.append('storage_unavailable')
        if default_bridge:
            br_nodes = {str(n.get('node')) for n in networks if n.get('bridge') == default_bridge}
            if node_name not in br_nodes:
                reasons.append('bridge_unavailable')
        excluded_reasons[node_name] = reasons or ['policy_filtered']
    recommended_next_steps = []
    if failures:
        recommended_next_steps.append('Fix FAIL conditions before provisioning.')
    if warnings:
        recommended_next_steps.append('Use prefer_default_then_balance or manual policy until assets are available cluster-wide.')
    if template_vmid and len(eligible_nodes) <= 1:
        recommended_next_steps.append('Replicate/prepare template on additional nodes or use shared template storage.')
    if default_storage:
        recommended_next_steps.append(f'Ensure storage {default_storage} exists and is active on intended target nodes.')
    if default_bridge:
        recommended_next_steps.append(f'Ensure bridge {default_bridge} exists on intended target nodes.')
    status = 'FAIL' if failures else ('WARN' if warnings else 'PASS')
    return {
        'status': status,
        'cluster': {'id': cluster.id, 'name': cluster.name, 'api_url': cluster.api_url, 'is_active': cluster.is_active},
        'defaults': {'default_node': getattr(defaults, 'default_node', None), 'default_storage': default_storage, 'default_bridge': default_bridge, 'default_template_vmid': template_vmid, 'placement_policy': policy, 'clone_mode': getattr(defaults, 'clone_mode', None)},
        'nodes': nodes,
        'storage': storage,
        'templates': templates,
        'networks': networks,
        'isos': isos_result.get('items', []),
        'eligible_nodes': sorted(eligible_nodes),
        'excluded_nodes': excluded_nodes,
        'excluded_node_reasons': excluded_reasons,
        'warnings': warnings,
        'failures': failures,
        'recommended_next_steps': recommended_next_steps,
    }


@router.get('/admin/proxmox/assets/readiness')
async def assets_readiness(_user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    active = db.query(ProxmoxCluster).filter(ProxmoxCluster.is_active.is_(True)).first()
    if not active:
        raise HTTPException(status_code=404, detail='No active Proxmox cluster configured')
    return await cluster_readiness(active.id, _user=_user, db=db)


@router.post('/admin/proxmox/assets/sync-plan')
async def assets_sync_plan(payload: dict, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    return {'ok': True, 'status': 'dry_run', 'supported': False, 'message': 'Sync plan is dry-run only. Use Proxmox native replication/shared storage for real sync.', 'request': payload or {}}


@router.post('/admin/proxmox/assets/sync-template')
async def assets_sync_template(payload: dict, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    if not payload.get('confirm'):
        raise HTTPException(status_code=400, detail={'error': 'confirm=true required for explicit admin sync action'})
    return {'ok': False, 'status': 'unsupported', 'supported': False, 'message': 'Automated template sync is not enabled in cloud-safe mode. Use shared storage or manual Proxmox replication.'}


@router.post('/admin/proxmox/assets/sync-iso')
async def assets_sync_iso(payload: dict, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    if not payload.get('confirm'):
        raise HTTPException(status_code=400, detail={'error': 'confirm=true required for explicit admin sync action'})
    return {'ok': False, 'status': 'unsupported', 'supported': False, 'message': 'Automated ISO/media sync is not enabled in cloud-safe mode. Use shared storage or manual Proxmox copy.'}
