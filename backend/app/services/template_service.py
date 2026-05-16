from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.services.rbac import get_role_name
from app.models.models import VMTemplate, Permission


def list_templates(db: Session, user):
    if get_role_name(user) in ['Teacher', 'Admin']:
        return db.query(VMTemplate).all()
    return db.query(VMTemplate).join(Permission, Permission.template_id == VMTemplate.id).filter(Permission.user_id == user.id, VMTemplate.enabled.is_(True)).all()


def create_template(db: Session, payload):
    t = VMTemplate(**payload.model_dump())
    db.add(t); db.commit(); db.refresh(t)
    return t


def patch_template(db: Session, id: int, payload):
    t = db.query(VMTemplate).filter(VMTemplate.id == id).first()
    if not t:
        raise HTTPException(status_code=404, detail='Template not found')
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(t, k, v)
    db.commit(); db.refresh(t)
    return t
