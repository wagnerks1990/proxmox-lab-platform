from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.models import Class, Enrollment, Lab, OrganizationMembership, User, DesktopPool
from app.schemas.common import ApiEnvelope
from app.schemas.classes_labs import (
    ClassCreate, ClassOut, ClassPatch, EnrollmentCreate, EnrollmentOut,
    LabCreate, LabOut, LabPatch,
)
from app.services.rbac import get_role_name
from app.api.routers.pools import _attach_pool_readiness_hints, _attach_pool_counts
from app.services.organization_access import OrganizationContext, get_current_organization

router = APIRouter()


def _ensure_admin(user):
    if get_role_name(user) != 'Admin':
        raise HTTPException(status_code=403, detail='Forbidden')


@router.get('/admin/classes', response_model=ApiEnvelope[list[ClassOut]])
def list_classes(_user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    return ApiEnvelope(success=True, data=db.query(Class).filter(Class.organization_id == organization.id).order_by(Class.id.desc()).all())


@router.post('/admin/classes', response_model=ApiEnvelope[ClassOut])
def create_class(payload: ClassCreate, _user=Depends(require_role('Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    _ensure_admin(_user)
    if not payload.name.strip():
        raise HTTPException(status_code=422, detail='Class name is required')
    if payload.instructor_id is not None:
        instructor = db.query(OrganizationMembership).filter(
            OrganizationMembership.organization_id == organization.id,
            OrganizationMembership.user_id == payload.instructor_id,
            OrganizationMembership.is_active.is_(True),
            OrganizationMembership.role.in_(['instructor', 'admin', 'owner']),
        ).first()
        if not instructor:
            raise HTTPException(status_code=422, detail='instructor must be an active instructor in this organization')
    row = Class(organization_id=organization.id, **payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return ApiEnvelope(success=True, data=row)


@router.get('/admin/classes/{id}', response_model=ApiEnvelope[ClassOut])
def get_class(id: int, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    row = db.query(Class).filter(Class.id == id, Class.organization_id == organization.id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Class not found')
    return ApiEnvelope(success=True, data=row)


@router.patch('/admin/classes/{id}', response_model=ApiEnvelope[ClassOut])
def patch_class(id: int, payload: ClassPatch, _user=Depends(require_role('Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    _ensure_admin(_user)
    row = db.query(Class).filter(Class.id == id, Class.organization_id == organization.id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Class not found')
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(row, k, v)
    db.commit(); db.refresh(row)
    return ApiEnvelope(success=True, data=row)


@router.delete('/admin/classes/{id}', response_model=ApiEnvelope[dict])
def delete_class(id: int, _user=Depends(require_role('Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    _ensure_admin(_user)
    row = db.query(Class).filter(Class.id == id, Class.organization_id == organization.id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Class not found')
    if db.query(Enrollment).filter(Enrollment.class_id == id).first() or db.query(Lab).filter(Lab.class_id == id).first():
        raise HTTPException(status_code=409, detail='Cannot delete class with labs or enrollments')
    db.delete(row); db.commit()
    return ApiEnvelope(success=True, data={'deleted': True, 'id': id})


@router.get('/admin/classes/{id}/enrollments', response_model=ApiEnvelope[list[EnrollmentOut]])
def list_enrollments(id: int, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    if not db.query(Class).filter(Class.id == id, Class.organization_id == organization.id).first():
        raise HTTPException(status_code=404, detail='Class not found')
    return ApiEnvelope(success=True, data=db.query(Enrollment).filter(Enrollment.class_id == id).all())


@router.post('/admin/classes/{id}/enrollments', response_model=ApiEnvelope[EnrollmentOut])
def add_enrollment(id: int, payload: EnrollmentCreate, _user=Depends(require_role('Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    _ensure_admin(_user)
    if not db.query(Class).filter(Class.id == id, Class.organization_id == organization.id).first():
        raise HTTPException(status_code=404, detail='Class not found')
    if not db.query(OrganizationMembership).filter(OrganizationMembership.organization_id == organization.id, OrganizationMembership.user_id == payload.user_id, OrganizationMembership.is_active.is_(True)).first():
        raise HTTPException(status_code=422, detail='user must be an active member of this organization')
    existing = db.query(Enrollment).filter(Enrollment.class_id == id, Enrollment.user_id == payload.user_id).first()
    if existing:
        return ApiEnvelope(success=True, data=existing)
    row = Enrollment(class_id=id, user_id=payload.user_id, role=payload.role)
    db.add(row); db.commit(); db.refresh(row)
    return ApiEnvelope(success=True, data=row)


@router.delete('/admin/classes/{id}/enrollments/{user_id}', response_model=ApiEnvelope[dict])
def remove_enrollment(id: int, user_id: int, _user=Depends(require_role('Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    _ensure_admin(_user)
    if not db.query(Class).filter(Class.id == id, Class.organization_id == organization.id).first():
        raise HTTPException(status_code=404, detail='Class not found')
    row = db.query(Enrollment).filter(Enrollment.class_id == id, Enrollment.user_id == user_id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Enrollment not found')
    db.delete(row); db.commit()
    return ApiEnvelope(success=True, data={'deleted': True, 'class_id': id, 'user_id': user_id})


async def _with_readiness(db: Session, lab: Lab) -> Lab:
    pool = db.query(DesktopPool).filter(DesktopPool.id == lab.default_pool_id, DesktopPool.organization_id == lab.organization_id).first()
    if pool:
        pool = await _attach_pool_readiness_hints(db, _attach_pool_counts(db, pool))
        lab.readiness_status = pool.readiness_status
        lab.placement_warning = pool.placement_warning
        lab.asset_ready_nodes = pool.asset_ready_nodes
        lab.constrained_nodes = pool.constrained_nodes
        lab.missing_templates_by_node = pool.missing_templates_by_node
        lab.missing_isos_by_node = pool.missing_isos_by_node
        lab.recommended_next_steps = pool.recommended_next_steps
        lab.assets_page_hint = '/admin/proxmox/assets'
    return lab


@router.get('/admin/labs', response_model=ApiEnvelope[list[LabOut]])
async def list_labs(_user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    rows = db.query(Lab).filter(Lab.organization_id == organization.id).order_by(Lab.id.desc()).all()
    return ApiEnvelope(success=True, data=[await _with_readiness(db, r) for r in rows])


@router.post('/admin/labs', response_model=ApiEnvelope[LabOut])
async def create_lab(payload: LabCreate, _user=Depends(require_role('Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    _ensure_admin(_user)
    if payload.starts_at and payload.ends_at and payload.starts_at >= payload.ends_at:
        raise HTTPException(status_code=422, detail='starts_at must be before ends_at')
    if not db.query(Class).filter(Class.id == payload.class_id, Class.organization_id == organization.id).first():
        raise HTTPException(status_code=422, detail='class_id not found')
    if not db.query(DesktopPool).filter(DesktopPool.id == payload.default_pool_id, DesktopPool.organization_id == organization.id).first():
        raise HTTPException(status_code=422, detail='default_pool_id not found')
    row = Lab(organization_id=organization.id, **payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return ApiEnvelope(success=True, data=await _with_readiness(db, row))


@router.get('/admin/labs/{id}', response_model=ApiEnvelope[LabOut])
async def get_lab(id: int, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    row = db.query(Lab).filter(Lab.id == id, Lab.organization_id == organization.id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Lab not found')
    return ApiEnvelope(success=True, data=await _with_readiness(db, row))


@router.patch('/admin/labs/{id}', response_model=ApiEnvelope[LabOut])
async def patch_lab(id: int, payload: LabPatch, _user=Depends(require_role('Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    _ensure_admin(_user)
    row = db.query(Lab).filter(Lab.id == id, Lab.organization_id == organization.id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Lab not found')
    merged = {**row.__dict__, **payload.model_dump(exclude_none=True)}
    if merged.get('starts_at') and merged.get('ends_at') and merged.get('starts_at') >= merged.get('ends_at'):
        raise HTTPException(status_code=422, detail='starts_at must be before ends_at')
    if payload.default_pool_id is not None and not db.query(DesktopPool).filter(DesktopPool.id == payload.default_pool_id, DesktopPool.organization_id == organization.id).first():
        raise HTTPException(status_code=422, detail='default_pool_id not found')
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(row, k, v)
    db.commit(); db.refresh(row)
    return ApiEnvelope(success=True, data=await _with_readiness(db, row))


@router.delete('/admin/labs/{id}', response_model=ApiEnvelope[dict])
def delete_lab(id: int, _user=Depends(require_role('Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    _ensure_admin(_user)
    row = db.query(Lab).filter(Lab.id == id, Lab.organization_id == organization.id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Lab not found')
    db.delete(row); db.commit()
    return ApiEnvelope(success=True, data={'deleted': True, 'id': id})
