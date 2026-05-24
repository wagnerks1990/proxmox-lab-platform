from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from datetime import datetime, timezone
from app.models.models import ProxmoxCluster, AssetSyncJob, AssetSyncJobEvent, AssetCatalog
from app.schemas.assets import SyncIsoRequest, SyncCtTemplateRequest, SyncVmTemplateRequest
from app.services.asset_sync import AssetSyncService
from app.services.proxmox_assets import ProxmoxAssetsService

router = APIRouter()


@router.get('/admin/proxmox/assets/inventory')
async def assets_inventory(_user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    active = db.query(ProxmoxCluster).filter(ProxmoxCluster.is_active.is_(True)).first()
    if not active:
        raise HTTPException(status_code=404, detail='No active Proxmox cluster configured')
    svc = ProxmoxAssetsService()
    nodes = await svc.discover_nodes()
    node_names = [n['node'] for n in nodes if n.get('node')]
    iso, ct, vm, errors = [], [], [], {}
    for n in node_names:
        try:
            iso.extend(await svc.discover_isos_by_node([n], 'local'))
        except Exception as e:
            errors.setdefault(n, []).append(f'iso inventory failed: {e}')
        try:
            ct.extend(await svc.discover_ct_templates_by_node([n], 'local'))
        except Exception as e:
            errors.setdefault(n, []).append(f'ct inventory failed: {e}')
        try:
            vm.extend(await svc.discover_vm_templates_by_node([n]))
        except Exception as e:
            errors.setdefault(n, []).append(f'vm template inventory failed: {e}')
    return {'nodes': nodes, 'storages': ['local', 'local-lvm'], 'iso_by_node': iso, 'ct_templates_by_node': ct, 'vm_templates_by_node': vm, 'errors_by_node': errors, 'generated_at': datetime.now(timezone.utc).isoformat()}


@router.get('/admin/proxmox/assets/readiness')
async def assets_readiness(_user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    inv = await assets_inventory(_user=_user, db=db)
    nodes = [n['node'] for n in inv.get('nodes', []) if (n.get('status') or '').lower() in {'online', 'up'}]

    def missing_by_node(groups, item_key):
        union = set()
        by = {}
        for g in groups:
            vals = set([x.get(item_key) for x in g.get('items', []) if x.get(item_key)])
            by[g.get('node')] = vals
            union |= vals
        out = {}
        for n in nodes:
            missing = sorted(list(union - by.get(n, set())))
            if missing:
                out[n] = missing
        return out

    missing_isos = missing_by_node(inv.get('iso_by_node', []), 'filename')
    missing_ct = missing_by_node(inv.get('ct_templates_by_node', []), 'volid')

    vm_union = set()
    vm_by_node = {}
    for g in inv.get('vm_templates_by_node', []):
        names = set([x.get('name') for x in g.get('templates', []) if x.get('name')])
        vm_union |= names
        vm_by_node[g.get('node')] = names
    missing_vm = {}
    for n in nodes:
        m = sorted(list(vm_union - vm_by_node.get(n, set())))
        if m:
            missing_vm[n] = m

    constrained = sorted(set(list(missing_isos.keys()) + list(missing_ct.keys()) + list(missing_vm.keys())))
    ready = sorted([n for n in nodes if n not in constrained])
    required_assets = db.query(AssetCatalog).filter(AssetCatalog.is_required.is_(True)).all()
    status = 'PASS' if (len(constrained) == 0 and len(required_assets) > 0) else ('WARN' if len(nodes) > 0 else 'FAIL')
    if len(required_assets) == 0:
        status = 'WARN'
    return {
        'ok': len(constrained) == 0 and len(required_assets) > 0,
        'status': status,
        'asset_ready_nodes': ready,
        'constrained_nodes': constrained,
        'missing_isos_by_node': missing_isos,
        'missing_ct_templates_by_node': missing_ct,
        'missing_vm_templates_by_node': missing_vm,
        'vm_template_vmid_by_node': {
            t.get('name'): {g.get('node'): x.get('vmid') for g in inv.get('vm_templates_by_node', []) for x in g.get('templates', []) if x.get('name') == t.get('name')}
            for g in inv.get('vm_templates_by_node', []) for t in g.get('templates', [])
        },
        'errors_by_node': inv.get('errors_by_node', {}),
        'recommended_next_steps': [
            'Sync missing assets to constrained nodes.',
            'Use local-only placement constraints until assets are verified on each target node.',
        ] if constrained else (['No required assets are configured in asset_catalog yet.'] if len(required_assets) == 0 else ['All required assets are present on all online nodes.'])
    }


@router.post('/admin/proxmox/assets/sync/iso')
async def sync_iso(payload: SyncIsoRequest, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    jobs = await AssetSyncService(db).sync_iso(payload.filename, payload.storage_id, payload.source_url, payload.target_nodes)
    return {'jobs': [{'job_id': j.id, 'state': j.state, 'method': j.method, 'target_node': j.target_node, 'proxmox_upid': j.proxmox_upid} for j in jobs]}


@router.post('/admin/proxmox/assets/sync/ct-template')
async def sync_ct_template(payload: SyncCtTemplateRequest, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    jobs = await AssetSyncService(db).sync_ct_template(payload.filename, payload.storage_id, payload.source_url, payload.target_nodes)
    return {'jobs': [{'job_id': j.id, 'state': j.state, 'method': j.method, 'target_node': j.target_node, 'proxmox_upid': j.proxmox_upid} for j in jobs]}


@router.post('/admin/proxmox/assets/sync/vm-template')
async def sync_vm_template(payload: SyncVmTemplateRequest, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    jobs = await AssetSyncService(db).sync_vm_template(payload.source_node, payload.source_vmid, payload.template_name, payload.storage_id, payload.target_nodes)
    return {'jobs': [{'job_id': j.id, 'state': j.state, 'method': j.method, 'target_node': j.target_node, 'error': j.error} for j in jobs]}


@router.get('/admin/proxmox/assets/sync-jobs/{job_id}')
async def sync_job(job_id: int, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    job = db.query(AssetSyncJob).filter(AssetSyncJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail='job not found')
    events = db.query(AssetSyncJobEvent).filter(AssetSyncJobEvent.job_id == job_id).order_by(AssetSyncJobEvent.id.asc()).all()
    return {
        'job': {
            'id': job.id, 'asset_id': job.asset_id, 'state': job.state, 'method': job.method, 'target_node': job.target_node,
            'source_node': job.source_node, 'source_vmid': job.source_vmid, 'target_vmid': job.target_vmid,
            'proxmox_upid': job.proxmox_upid, 'started_at': job.started_at, 'finished_at': job.finished_at, 'error': job.error,
        },
        'events': [{'id': e.id, 'level': e.level, 'message': e.message, 'metadata': e.metadata_json, 'created_at': e.created_at} for e in events]
    }
