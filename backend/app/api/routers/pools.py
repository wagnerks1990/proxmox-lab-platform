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

router = APIRouter()


def _attach_pool_counts(db: Session, row: DesktopPool) -> DesktopPool:
    if row.template_vmid:
        tpl = db.query(VMTemplate).filter(VMTemplate.source_vmid == row.template_vmid).first()
        row.linked_vm_count = db.query(StudentVM).filter(StudentVM.template_id == tpl.id).count() if tpl else 0
    else:
        row.linked_vm_count = 0
    row.linked_template_count = 1 if row.template_vmid else 0
    row.linked_group_count = (
        db.query(GroupTemplatePermission)
        .join(VMTemplate, VMTemplate.id == GroupTemplatePermission.template_id)
        .filter(VMTemplate.source_vmid == row.template_vmid)
        .count()
        if row.template_vmid
        else 0
    )
    return row


@router.get('/pools', response_model=ApiEnvelope[list[PoolOut]])
def list_pools(_user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    rows = db.query(DesktopPool).order_by(DesktopPool.id.desc()).all()
    return ApiEnvelope(success=True, data=[_attach_pool_counts(db, r) for r in rows])


@router.post('/pools', response_model=ApiEnvelope[PoolOut])
async def create_pool(payload: PoolCreate, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    svc = PoolService(db)
    data = payload.model_dump()
    errs = svc.validate_pool_config(data)
    if errs:
        raise HTTPException(status_code=422, detail={'errors': errs})
    if data.get('template_vmid'):
        tpl = db.query(VMTemplate).filter(VMTemplate.source_vmid == data['template_vmid']).first()
        if not tpl:
            raise HTTPException(status_code=422, detail='Import Proxmox templates before creating pools.')
        if not data.get('template_node'):
            data['template_node'] = tpl.proxmox_node
    row = DesktopPool(**data)
    db.add(row); db.commit(); db.refresh(row)
    return ApiEnvelope(success=True, data=_attach_pool_counts(db, row))


@router.get('/pools/{id}', response_model=ApiEnvelope[PoolOut])
def get_pool(id: int, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    row = db.query(DesktopPool).filter(DesktopPool.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Pool not found')
    return ApiEnvelope(success=True, data=_attach_pool_counts(db, row))


@router.patch('/pools/{id}', response_model=ApiEnvelope[PoolOut])
async def patch_pool(id: int, payload: PoolPatch, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    row = db.query(DesktopPool).filter(DesktopPool.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Pool not found')
    merged = {**row.__dict__, **payload.model_dump(exclude_none=True)}
    errs = PoolService(db).validate_pool_config(merged)
    if errs:
        raise HTTPException(status_code=422, detail={'errors': errs})
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(row, k, v)
    db.commit(); db.refresh(row)
    return ApiEnvelope(success=True, data=_attach_pool_counts(db, row))


@router.delete('/pools/{id}', response_model=ApiEnvelope[dict])
def delete_pool(id: int, force: bool = False, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    row = db.query(DesktopPool).filter(DesktopPool.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Pool not found')
    attached = db.query(StudentVM).filter(StudentVM.template_id.isnot(None)).count()
    if attached > 0 and not force:
        raise HTTPException(status_code=409, detail='Pool may have VM dependencies; pass force=true to remove app pool record')
    db.delete(row)
    db.commit()
    return ApiEnvelope(success=True, data={'deleted': True, 'id': id, 'message': 'Pool app record deleted. No Proxmox VMs were changed.'})


@router.patch('/pools/{id}/enabled', response_model=ApiEnvelope[PoolOut])
def patch_pool_enabled(id: int, payload: dict, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    row = db.query(DesktopPool).filter(DesktopPool.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Pool not found')
    row.enabled = bool(payload.get('enabled'))
    db.commit(); db.refresh(row)
    return ApiEnvelope(success=True, data=_attach_pool_counts(db, row))


@router.patch('/pools/{id}/maintenance', response_model=ApiEnvelope[PoolOut])
def patch_pool_maintenance(id: int, payload: dict, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    row = db.query(DesktopPool).filter(DesktopPool.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Pool not found')
    row.maintenance_mode = bool(payload.get('maintenance_mode'))
    db.commit(); db.refresh(row)
    return ApiEnvelope(success=True, data=_attach_pool_counts(db, row))


@router.get('/pools/{id}/members', response_model=ApiEnvelope[list[dict]])
def pool_members(id: int, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    row = db.query(DesktopPool).filter(DesktopPool.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Pool not found')
    return ApiEnvelope(success=True, data=[])


@router.get('/pools/{id}/readiness', response_model=ApiEnvelope[dict])
async def pool_readiness(id: int, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    row = db.query(DesktopPool).filter(DesktopPool.id == id).first()
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
        tpl = db.query(VMTemplate).filter(VMTemplate.source_vmid == row.template_vmid).first()
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
    return ApiEnvelope(success=True, data={'status': status, 'warnings': warnings, 'failures': failures, 'pool_enabled': row.enabled, 'maintenance_mode': row.maintenance_mode, 'eligible_nodes': nodes, 'default_node': getattr(defaults, 'default_node', None), 'default_storage': getattr(defaults, 'default_storage', None), 'default_bridge': getattr(defaults, 'default_bridge', None)})


@router.get('/pools/{id}/plan', response_model=ApiEnvelope[PoolPlanResponse])
def plan_pool(id: int, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    row = db.query(DesktopPool).filter(DesktopPool.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Pool not found')
    plan = PoolPlanningService().build_plan(row)
    return ApiEnvelope(success=True, data=plan)
