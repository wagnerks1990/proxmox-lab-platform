from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.models import DesktopPool
from app.schemas.common import ApiEnvelope
from app.schemas.pools import PoolCreate, PoolOut, PoolPatch
from app.services.pool_service import PoolService

router = APIRouter()


@router.get('/pools', response_model=ApiEnvelope[list[PoolOut]])
def list_pools(_user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    return ApiEnvelope(success=True, data=db.query(DesktopPool).order_by(DesktopPool.id.desc()).all())


@router.post('/pools', response_model=ApiEnvelope[PoolOut])
def create_pool(payload: PoolCreate, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    svc = PoolService(db)
    errs = svc.validate_pool_config(payload.model_dump())
    if errs:
        raise HTTPException(status_code=422, detail={'errors': errs})
    row = DesktopPool(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return ApiEnvelope(success=True, data=row)


@router.get('/pools/{id}', response_model=ApiEnvelope[PoolOut])
def get_pool(id: int, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
    row = db.query(DesktopPool).filter(DesktopPool.id == id).first()
    if not row:
        raise HTTPException(status_code=404, detail='Pool not found')
    return ApiEnvelope(success=True, data=row)


@router.patch('/pools/{id}', response_model=ApiEnvelope[PoolOut])
def patch_pool(id: int, payload: PoolPatch, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db)):
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
    return ApiEnvelope(success=True, data=row)
