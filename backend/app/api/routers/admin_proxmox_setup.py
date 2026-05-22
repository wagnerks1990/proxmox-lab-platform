from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.models import ProxmoxCluster, ProxmoxNode, ProxmoxClusterDefault
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
