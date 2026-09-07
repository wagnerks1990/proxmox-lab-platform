from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.models import DesktopPool, VMTemplate, ProxmoxCluster, ProxmoxNode, ProxmoxClusterDefault, StudentVM, GroupTemplatePermission
from app.schemas.common import ApiEnvelope
from app.schemas.pools import PoolCreate, PoolOut, PoolPatch
from app.services.pool_service import PoolService
from app.services.pool_planning_service import PoolPlanningService
from app.schemas.pool_plan import PoolPlanResponse
from app.services.proxmox_bootstrap import ProxmoxBootstrapService
from app.services.rbac import get_role_name
from app.services.organization_access import OrganizationContext, get_current_organization

router = APIRouter()


def _attach_pool_counts(db: Session, row: DesktopPool) -> DesktopPool:
    if row.template_vmid:
        tpl = db.query(VMTemplate).filter(VMTemplate.source_vmid == row.template_vmid, VMTemplate.organization_id == row.organization_id).first()
        row.linked_vm_count = db.query(StudentVM).filter(StudentVM.template_id == tpl.id, StudentVM.organization_id == row.organization_id).count() if tpl else 0
    else:
        row.linked_vm_count = 0
    row.linked_template_count = 1 if row.template_vmid else 0
    row.linked_group_count = (
        db.query(GroupTemplatePermission)
        .join(VMTemplate, VMTemplate.id == GroupTemplatePermission.template_id)
        .filter(VMTemplate.source_vmid == row.template_vmid, VMTemplate.organization_id == row.organization_id)
        .count()
        if row.template_vmid
        else 0
    )
    return row


async def _attach_pool_readiness_hints(db: Session, row: DesktopPool) -> DesktopPool:
    row.readiness_status = None
    row.placement_warning = None
    row.asset_ready_nodes = []
    row.constrained_nodes = []
    row.missing_templates_by_node = {}
    row.missing_isos_by_node = {}
    row.recommended_next_steps = []
    active = db.query(ProxmoxCluster).filter(ProxmoxCluster.is_active.is_(True)).first()
    if not active:
        row.readiness_status = 'FAIL'
        row.placement_warning = 'No active Proxmox cluster configured.'
        row.recommended_next_steps = ['Configure and activate a Proxmox cluster before using this pool.']
        return row
    svc = ProxmoxBootstrapService(db)
    templates = await svc.discover_templates(active)
    isos = await svc.discover_isos(active)
    nodes = [n.node_name for n in db.query(ProxmoxNode).filter(ProxmoxNode.cluster_id == active.id).all() if (n.status or '').lower() in {'online', 'up'}]
    template_nodes = {str(t.get('node')) for t in templates if row.template_vmid and int(t.get('vmid', -1)) == int(row.template_vmid)}
    row.asset_ready_nodes = sorted(list(template_nodes)) if row.template_vmid else []
    row.constrained_nodes = sorted([n for n in nodes if n not in template_nodes]) if row.template_vmid else []
    if row.template_vmid:
        row.missing_templates_by_node = {n: [row.template_vmid] for n in row.constrained_nodes}
    else:
        row.missing_templates_by_node = {}
    iso_items = isos.get('items', [])
    iso_by_node = {}
    all_iso_ids = set()
    for i in iso_items:
        key = i.get('content_id') or i.get('name')
        if not key or not i.get('node'):
            continue
        all_iso_ids.add(str(key))
        iso_by_node.setdefault(str(i.get('node')), set()).add(str(key))
    row.missing_isos_by_node = {}
    for n in nodes:
        missing = sorted(list(all_iso_ids - iso_by_node.get(n, set())))
        if missing:
            row.missing_isos_by_node[n] = missing
    defaults = db.query(ProxmoxClusterDefault).filter(ProxmoxClusterDefault.cluster_id == active.id).first()
    policy = getattr(defaults, 'placement_policy', None)
    if policy == 'balanced' and row.constrained_nodes:
        row.readiness_status = 'WARN'
        row.placement_warning = 'Balanced placement is constrained because required assets are not available on all eligible nodes.'
        row.recommended_next_steps = [
            'Use shared storage for templates/ISOs.',
            'Replicate or prepare required assets on all eligible nodes.',
            f'Constrain placement to asset-ready nodes ({", ".join(row.asset_ready_nodes) or "none"}) until assets are available cluster-wide.',
        ]
    else:
        row.readiness_status = 'PASS'
    return row


@router.get('/pools', response_model=ApiEnvelope[list[PoolOut]])
@router.get('/admin/pools', response_model=ApiEnvelope[list[PoolOut]])
async def list_pools(_user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    if get_role_name(_user) not in {'Teacher', 'Admin'}:
        raise HTTPException(status_code=403, detail='Forbidden')
    rows = db.query(DesktopPool).filter(DesktopPool.organization_id == organization.id).order_by(DesktopPool.id.desc()).all()
    out = []
    for r in rows:
        out.append(await _attach_pool_readiness_hints(db, _attach_pool_counts(db, r)))
    return ApiEnvelope(success=True, data=out)


@router.post('/pools', response_model=ApiEnvelope[PoolOut])
@router.post('/admin/pools', response_model=ApiEnvelope[PoolOut])
async def create_pool(payload: PoolCreate, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    if get_role_name(_user) not in {'Teacher', 'Admin'}:
        raise HTTPException(status_code=403, detail='Forbidden')
    svc = PoolService(db)
    data = payload.model_dump()
    if not data.get('name'):
        raise HTTPException(status_code=422, detail={'errors': ['name is required']})
    size_min = int((data.get('size_min') or 0))
    size_max = int((data.get('size_max') or data.get('desired_size') or 0))
    if size_min < 0 or size_max < 0 or size_min > size_max:
        raise HTTPException(status_code=422, detail={'errors': ['size_min/size_max must be non-negative and size_min <= size_max']})
    errs = svc.validate_pool_config(data)
    if errs:
        raise HTTPException(status_code=422, detail={'errors': errs})
    if data.get('template_vmid'):
        tpl = db.query(VMTemplate).filter(VMTemplate.source_vmid == data['template_vmid'], VMTemplate.organization_id == organization.id).first()
        if not tpl:
            raise HTTPException(status_code=422, detail='Import Proxmox templates before creating pools.')
        if not data.get('template_node'):
            data['template_node'] = tpl.proxmox_node
    row = DesktopPool(organization_id=organization.id, **data)
    db.add(row); db.commit(); db.refresh(row)
    _write_audit(db, _user.id, organization.id, 'POOL_CREATED', str(row.id), f'Pool {row.name} created')
    return ApiEnvelope(success=True, data=await _attach_pool_readiness_hints(db, _attach_pool_counts(db, row)))


@router.get('/pools/{id}', response_model=ApiEnvelope[PoolOut])
@router.get('/admin/pools/{id}', response_model=ApiEnvelope[PoolOut])
async def get_pool(id: int, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    if get_role_name(_user) not in {'Teacher', 'Admin'}:
        raise HTTPException(status_code=403, detail='Forbidden')
    row = db.query(DesktopPool).filter(DesktopPool.id == id, DesktopPool.organization_id == organization.id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Pool not found')
    return ApiEnvelope(success=True, data=await _attach_pool_readiness_hints(db, _attach_pool_counts(db, row)))


@router.patch('/pools/{id}', response_model=ApiEnvelope[PoolOut])
@router.patch('/admin/pools/{id}', response_model=ApiEnvelope[PoolOut])
async def patch_pool(id: int, payload: PoolPatch, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    if get_role_name(_user) not in {'Teacher', 'Admin'}:
        raise HTTPException(status_code=403, detail='Forbidden')
    row = db.query(DesktopPool).filter(DesktopPool.id == id, DesktopPool.organization_id == organization.id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Pool not found')
    merged = {**row.__dict__, **payload.model_dump(exclude_none=True)}
    errs = PoolService(db).validate_pool_config(merged)
    if errs:
        raise HTTPException(status_code=422, detail={'errors': errs})
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(row, k, v)
    db.commit(); db.refresh(row)
    _write_audit(db, _user.id, organization.id, 'POOL_UPDATED', str(row.id), f'Pool {row.name} updated')
    return ApiEnvelope(success=True, data=await _attach_pool_readiness_hints(db, _attach_pool_counts(db, row)))


@router.delete('/pools/{id}', response_model=ApiEnvelope[dict])
@router.delete('/admin/pools/{id}', response_model=ApiEnvelope[dict])
def delete_pool(id: int, force: bool = False, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    if get_role_name(_user) not in {'Teacher', 'Admin'}:
        raise HTTPException(status_code=403, detail='Forbidden')
    row = db.query(DesktopPool).filter(DesktopPool.id == id, DesktopPool.organization_id == organization.id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Pool not found')
    tpl = db.query(VMTemplate).filter(VMTemplate.source_vmid == row.template_vmid, VMTemplate.organization_id == organization.id).first() if row.template_vmid else None
    attached = db.query(StudentVM).filter(StudentVM.template_id == tpl.id, StudentVM.organization_id == organization.id).count() if tpl else 0
    if attached > 0 and not force:
        raise HTTPException(status_code=409, detail='Pool may have VM dependencies; pass force=true to remove app pool record')
    _write_audit(db, _user.id, organization.id, 'POOL_DELETED', str(row.id), f'Pool {row.name} deleted')
    db.delete(row)
    db.commit()
    return ApiEnvelope(success=True, data={'deleted': True, 'id': id, 'message': 'Pool app record deleted. No Proxmox VMs were changed.'})


@router.patch('/pools/{id}/enabled', response_model=ApiEnvelope[PoolOut])
def patch_pool_enabled(id: int, payload: dict, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    row = db.query(DesktopPool).filter(DesktopPool.id == id, DesktopPool.organization_id == organization.id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Pool not found')
    row.enabled = bool(payload.get('enabled'))
    db.commit(); db.refresh(row)
    return ApiEnvelope(success=True, data=_attach_pool_counts(db, row))


@router.patch('/pools/{id}/maintenance', response_model=ApiEnvelope[PoolOut])
def patch_pool_maintenance(id: int, payload: dict, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    row = db.query(DesktopPool).filter(DesktopPool.id == id, DesktopPool.organization_id == organization.id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Pool not found')
    row.maintenance_mode = bool(payload.get('maintenance_mode'))
    db.commit(); db.refresh(row)
    return ApiEnvelope(success=True, data=_attach_pool_counts(db, row))


@router.get('/pools/{id}/members', response_model=ApiEnvelope[list[dict]])
def pool_members(id: int, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    row = db.query(DesktopPool).filter(DesktopPool.id == id, DesktopPool.organization_id == organization.id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Pool not found')
    return ApiEnvelope(success=True, data=[])


@router.get('/pools/{id}/readiness', response_model=ApiEnvelope[dict])
async def pool_readiness(id: int, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    row = db.query(DesktopPool).filter(DesktopPool.id == id, DesktopPool.organization_id == organization.id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Pool not found')
    warnings, failures = [], []
    active = db.query(ProxmoxCluster).filter(ProxmoxCluster.is_active.is_(True)).first()
    if not active:
        failures.append('No active Proxmox cluster configured.')
    nodes = [n.node_name for n in db.query(ProxmoxNode).filter(ProxmoxNode.cluster_id == (active.id if active else -1)).all()]
    if row.desired_size == 0:
        warnings.append('Desired count is 0.')
    if not row.template_vmid:
        failures.append('No template selected.')
    else:
        tpl = db.query(VMTemplate).filter(VMTemplate.source_vmid == row.template_vmid, VMTemplate.organization_id == organization.id).first()
        if not tpl:
            failures.append('Selected template is not imported in app vm_templates.')
        if active:
            discovered = await ProxmoxBootstrapService(db).discover_templates(active)
            template_nodes = sorted({str(t.get('node')) for t in discovered if t.get('vmid') == row.template_vmid and t.get('node')})
            missing_nodes = [n for n in nodes if n not in template_nodes]
            if not template_nodes:
                failures.append(f'Template VMID {row.template_vmid} was not found in live Proxmox discovery.')
            elif missing_nodes:
                warnings.append(f'Template VMID {row.template_vmid} is not on all nodes; missing: {", ".join(missing_nodes)}.')
    status = 'PASS'
    if failures:
        status = 'FAIL'
    elif warnings:
        status = 'WARN'
    defaults = db.query(ProxmoxClusterDefault).filter(ProxmoxClusterDefault.cluster_id == (active.id if active else -1)).first()
    recommended_next_steps = []
    if failures:
        recommended_next_steps.append('Resolve FAIL conditions before provisioning from this pool.')
    if any('not on all nodes' in w for w in warnings):
        recommended_next_steps.append('Balanced placement may be limited until template availability is expanded or shared storage is used.')
    return ApiEnvelope(success=True, data={'status': status, 'warnings': warnings, 'failures': failures, 'recommended_next_steps': recommended_next_steps, 'pool_enabled': row.enabled, 'maintenance_mode': row.maintenance_mode, 'eligible_nodes': nodes, 'default_node': getattr(defaults, 'default_node', None), 'default_storage': getattr(defaults, 'default_storage', None), 'default_bridge': getattr(defaults, 'default_bridge', None)})


@router.get('/pools/{id}/plan', response_model=ApiEnvelope[PoolPlanResponse])
def plan_pool(id: int, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    row = db.query(DesktopPool).filter(DesktopPool.id == id, DesktopPool.organization_id == organization.id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Pool not found')
    plan = PoolPlanningService().build_plan(row)
    return ApiEnvelope(success=True, data=plan)
def _write_audit(db: Session, actor_id: int, organization_id: int, action: str, target_id: str, details: str | None = None):
    try:
        from app.models.models import AuditLog
        row = AuditLog(organization_id=organization_id, actor_id=actor_id, action=action, target_type='desktop_pool', target_id=target_id)
        db.add(row)
        if details:
            # Keep details in action text if separate column is unavailable in schema.
            row.action = f'{action}: {details}'
    except Exception:
        pass
