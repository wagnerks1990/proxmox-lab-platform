from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.models import (
    DesktopPool,
    Group,
    ProxmoxCluster,
    ProxmoxNode,
    ProxmoxClusterDefault,
    StudentVM,
    User,
    VMTemplate,
    VMSession,
    AuditLog,
)
from app.services.health_service import health_summary
from app.services.rbac import get_role_name
from app.services.organization_access import OrganizationContext, get_current_organization

router = APIRouter()


@router.get('/admin/dashboard/summary')
async def dashboard_summary(_user=Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    if get_role_name(_user) not in {'Teacher', 'Admin'}:
        raise HTTPException(status_code=403, detail='Forbidden')
    health = await health_summary(db)
    active = db.query(ProxmoxCluster).filter(ProxmoxCluster.is_active.is_(True)).first()
    defaults = db.query(ProxmoxClusterDefault).filter(ProxmoxClusterDefault.cluster_id == (active.id if active else -1)).first()
    nodes = db.query(ProxmoxNode).filter(ProxmoxNode.cluster_id == (active.id if active else -1)).all() if active else []
    online_nodes = [n for n in nodes if (n.status or '').lower() in {'online', 'up'}]
    vms = db.query(StudentVM).filter(StudentVM.organization_id == organization.id).all()
    warnings = []
    if not db.query(VMTemplate).filter(VMTemplate.organization_id == organization.id).count():
        warnings.append({'severity': 'warning', 'title': 'No templates', 'message': 'No app templates are imported yet.', 'link': '/admin/proxmox-inventory'})
    if not db.query(DesktopPool).filter(DesktopPool.organization_id == organization.id).count():
        warnings.append({'severity': 'warning', 'title': 'No pools', 'message': 'No desktop pools are configured.', 'link': '/pools'})
    if active and not getattr(defaults, 'default_node', None):
        warnings.append({'severity': 'warning', 'title': 'Default node missing', 'message': 'Cluster default_node is not configured.', 'link': '/admin/proxmox-setup'})

    return {
        'health': {
            'backend': 'ok',
            'database': {'ok': bool(health.get('database', {}).get('ok')), 'error': health.get('database', {}).get('error')},
            'proxmox': {
                'ok': bool(health.get('proxmox', {}).get('ok')),
                'error': health.get('proxmox', {}).get('error'),
                'config_source': health.get('proxmox', {}).get('config_source'),
                'active_cluster_name': getattr(active, 'name', None),
                'nodes_discovered_count': len(nodes),
                'online_node_count': len(online_nodes),
                'credential_status': 'configured' if active else 'not_configured',
                'placement_policy': getattr(defaults, 'placement_policy', None) if defaults else None,
                'default_node': getattr(defaults, 'default_node', None) if defaults else None,
                'default_storage': getattr(defaults, 'default_storage', None) if defaults else None,
                'default_bridge': getattr(defaults, 'default_bridge', None) if defaults else None,
                'default_template_vmid': getattr(defaults, 'default_template_vmid', None) if defaults else None,
            },
        },
        'counts': {
            'templates': db.query(VMTemplate).filter(VMTemplate.organization_id == organization.id).count(),
            'pools': db.query(DesktopPool).filter(DesktopPool.organization_id == organization.id).count(),
            'groups': db.query(Group).filter(Group.organization_id == organization.id).count(),
            'users': db.query(User).count(),
            'vms': len(vms),
            'running_vms': len([v for v in vms if (v.status or '').lower() == 'running']),
            'nodes': len(nodes),
            'online_nodes': len(online_nodes),
            'sessions': db.query(VMSession).filter(VMSession.organization_id == organization.id).count(),
            'events': db.query(AuditLog).filter(AuditLog.organization_id == organization.id).count(),
        },
        'capacity': {'cpu_percent': None, 'memory_percent': None, 'storage_percent': None},
        'warnings': warnings,
        'recent_events': [
            {'id': a.id, 'time': (a.created_at or datetime.utcnow()).isoformat(), 'message': a.action}
            for a in db.query(AuditLog).filter(AuditLog.organization_id == organization.id).order_by(AuditLog.created_at.desc()).limit(10).all()
        ],
    }
