from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import Class, Enrollment, Lab, OrganizationMembership, User, DesktopPool
from app.schemas.common import ApiEnvelope
from app.schemas.classes_labs import (
    ClassCreate, ClassOut, ClassPatch, EnrollmentCreate, EnrollmentOut,
    LabCreate, LabOut, LabPatch,
)
from app.api.routers.pools import _attach_pool_readiness_hints, _attach_pool_counts
from app.services.organization_access import OrganizationContext, enforce_organization_role, organization_role_at_least, require_organization_role

router = APIRouter()


def _class_query(db: Session, organization: OrganizationContext, user):
    enforce_organization_role(organization, 'instructor')
    query = db.query(Class).filter(Class.organization_id == organization.id)
    if not organization_role_at_least(organization, 'admin'):
        query = query.filter(Class.instructor_id == user.id)
    return query


def _class_or_404(db: Session, class_id: int, organization: OrganizationContext, user) -> Class:
    row = _class_query(db, organization, user).filter(Class.id == class_id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Class not found')
    return row


def _validate_instructor(db: Session, organization_id: int, user_id: int) -> None:
    membership = db.query(OrganizationMembership).filter(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.user_id == user_id,
        OrganizationMembership.is_active.is_(True),
        OrganizationMembership.role.in_(['instructor', 'admin', 'owner']),
    ).first()
    if not membership:
        raise HTTPException(status_code=422, detail='instructor must be an active instructor in this organization')


@router.get('/admin/classes', response_model=ApiEnvelope[list[ClassOut]])
def list_classes(_user=Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(require_organization_role('instructor'))):
    return ApiEnvelope(success=True, data=_class_query(db, organization, _user).order_by(Class.id.desc()).all())


@router.post('/admin/classes', response_model=ApiEnvelope[ClassOut])
def create_class(payload: ClassCreate, _user=Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(require_organization_role('instructor'))):
    enforce_organization_role(organization, 'instructor')
    if not payload.name.strip():
        raise HTTPException(status_code=422, detail='Class name is required')
    data = payload.model_dump()
    if organization_role_at_least(organization, 'admin'):
        if data.get('instructor_id') is not None:
            _validate_instructor(db, organization.id, data['instructor_id'])
    else:
        if data.get('instructor_id') not in (None, _user.id):
            raise HTTPException(status_code=403, detail='Instructors may only create classes assigned to themselves')
        data['instructor_id'] = _user.id
    row = Class(organization_id=organization.id, **data)
    db.add(row); db.commit(); db.refresh(row)
    return ApiEnvelope(success=True, data=row)


@router.get('/admin/classes/{id}', response_model=ApiEnvelope[ClassOut])
def get_class(id: int, _user=Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(require_organization_role('instructor'))):
    row = _class_or_404(db, id, organization, _user)
    return ApiEnvelope(success=True, data=row)


@router.patch('/admin/classes/{id}', response_model=ApiEnvelope[ClassOut])
def patch_class(id: int, payload: ClassPatch, _user=Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(require_organization_role('instructor'))):
    row = _class_or_404(db, id, organization, _user)
    changes = payload.model_dump(exclude_none=True)
    if 'instructor_id' in changes:
        if not organization_role_at_least(organization, 'admin'):
            raise HTTPException(status_code=403, detail='Only organization administrators may reassign a class')
        _validate_instructor(db, organization.id, changes['instructor_id'])
    for k, v in changes.items():
        setattr(row, k, v)
    db.commit(); db.refresh(row)
    return ApiEnvelope(success=True, data=row)


@router.delete('/admin/classes/{id}', response_model=ApiEnvelope[dict])
def delete_class(id: int, _user=Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(require_organization_role('instructor'))):
    row = _class_or_404(db, id, organization, _user)
    if db.query(Enrollment).filter(Enrollment.class_id == id).first() or db.query(Lab).filter(Lab.class_id == id).first():
        raise HTTPException(status_code=409, detail='Cannot delete class with labs or enrollments')
    db.delete(row); db.commit()
    return ApiEnvelope(success=True, data={'deleted': True, 'id': id})


@router.get('/admin/classes/{id}/enrollments', response_model=ApiEnvelope[list[EnrollmentOut]])
def list_enrollments(id: int, _user=Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(require_organization_role('instructor'))):
    _class_or_404(db, id, organization, _user)
    return ApiEnvelope(success=True, data=db.query(Enrollment).filter(Enrollment.class_id == id).all())


@router.post('/admin/classes/{id}/enrollments', response_model=ApiEnvelope[EnrollmentOut])
def add_enrollment(id: int, payload: EnrollmentCreate, _user=Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(require_organization_role('instructor'))):
    _class_or_404(db, id, organization, _user)
    if not db.query(OrganizationMembership).filter(OrganizationMembership.organization_id == organization.id, OrganizationMembership.user_id == payload.user_id, OrganizationMembership.is_active.is_(True)).first():
        raise HTTPException(status_code=422, detail='user must be an active member of this organization')
    existing = db.query(Enrollment).filter(Enrollment.class_id == id, Enrollment.user_id == payload.user_id).first()
    if existing:
        return ApiEnvelope(success=True, data=existing)
    row = Enrollment(class_id=id, user_id=payload.user_id, role=payload.role)
    db.add(row); db.commit(); db.refresh(row)
    return ApiEnvelope(success=True, data=row)


@router.delete('/admin/classes/{id}/enrollments/{user_id}', response_model=ApiEnvelope[dict])
def remove_enrollment(id: int, user_id: int, _user=Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(require_organization_role('instructor'))):
    _class_or_404(db, id, organization, _user)
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
async def list_labs(_user=Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(require_organization_role('instructor'))):
    query = db.query(Lab).filter(Lab.organization_id == organization.id)
    if not organization_role_at_least(organization, 'admin'):
        own_class_ids = select(Class.id).where(Class.organization_id == organization.id, Class.instructor_id == _user.id)
        query = query.filter(Lab.class_id.in_(own_class_ids))
    rows = query.order_by(Lab.id.desc()).all()
    return ApiEnvelope(success=True, data=[await _with_readiness(db, r) for r in rows])


@router.post('/admin/labs', response_model=ApiEnvelope[LabOut])
async def create_lab(payload: LabCreate, _user=Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(require_organization_role('instructor'))):
    enforce_organization_role(organization, 'instructor')
    if payload.starts_at and payload.ends_at and payload.starts_at >= payload.ends_at:
        raise HTTPException(status_code=422, detail='starts_at must be before ends_at')
    try:
        _class_or_404(db, payload.class_id, organization, _user)
    except HTTPException as exc:
        raise HTTPException(status_code=422, detail='class_id not found or not managed by this instructor') from exc
    if not db.query(DesktopPool).filter(DesktopPool.id == payload.default_pool_id, DesktopPool.organization_id == organization.id).first():
        raise HTTPException(status_code=422, detail='default_pool_id not found')
    row = Lab(organization_id=organization.id, **payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return ApiEnvelope(success=True, data=await _with_readiness(db, row))


@router.get('/admin/labs/{id}', response_model=ApiEnvelope[LabOut])
async def get_lab(id: int, _user=Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(require_organization_role('instructor'))):
    row = db.query(Lab).filter(Lab.id == id, Lab.organization_id == organization.id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Lab not found')
    _class_or_404(db, row.class_id, organization, _user)
    return ApiEnvelope(success=True, data=await _with_readiness(db, row))


@router.patch('/admin/labs/{id}', response_model=ApiEnvelope[LabOut])
async def patch_lab(id: int, payload: LabPatch, _user=Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(require_organization_role('instructor'))):
    row = db.query(Lab).filter(Lab.id == id, Lab.organization_id == organization.id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Lab not found')
    _class_or_404(db, row.class_id, organization, _user)
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
def delete_lab(id: int, _user=Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(require_organization_role('instructor'))):
    row = db.query(Lab).filter(Lab.id == id, Lab.organization_id == organization.id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Lab not found')
    _class_or_404(db, row.class_id, organization, _user)
    db.delete(row); db.commit()
    return ApiEnvelope(success=True, data={'deleted': True, 'id': id})
