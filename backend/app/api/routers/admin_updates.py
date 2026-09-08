from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.services.deployment_updates import DeploymentUpdateService


router = APIRouter()


@router.get('/admin/system/update')
def update_status(_user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    return DeploymentUpdateService(db).status()


@router.patch('/admin/system/update/settings')
def update_settings(payload: dict, user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    row = DeploymentUpdateService(db).update_settings(payload, user.id)
    return {'branch': row.branch, 'channel': row.channel, 'automatic_updates': row.automatic_updates, 'check_interval_minutes': row.check_interval_minutes, 'maintenance_hour_utc': row.maintenance_hour_utc}


@router.post('/admin/system/update/check')
def check_update(user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    return DeploymentUpdateService(db).run('check', user.id)


@router.post('/admin/system/update/apply', status_code=status.HTTP_202_ACCEPTED)
def apply_update(payload: dict, user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    if payload.get('confirmation') != 'APPLY':
        raise HTTPException(status_code=422, detail='confirmation must equal APPLY')
    return DeploymentUpdateService(db).run('apply', user.id, payload.get('target_ref'))


@router.post('/admin/system/update/rollback', status_code=status.HTTP_202_ACCEPTED)
def rollback_update(payload: dict, user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    if payload.get('confirmation') != 'ROLLBACK':
        raise HTTPException(status_code=422, detail='confirmation must equal ROLLBACK')
    return DeploymentUpdateService(db).run('rollback', user.id)
