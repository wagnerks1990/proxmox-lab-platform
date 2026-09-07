from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.models import GroupMembership, GroupTemplatePermission, VMTemplate, Permission


def list_templates(db: Session, user, organization_id: int, organization_role: str):
    if organization_role in {'instructor', 'admin', 'owner'}:
        return db.query(VMTemplate).filter(VMTemplate.organization_id == organization_id).all()
    direct_ids = [row.template_id for row in db.query(Permission).filter(Permission.user_id == user.id).all()]
    group_ids = [row.template_id for row in db.query(GroupTemplatePermission).join(
        GroupMembership,
        GroupMembership.group_id == GroupTemplatePermission.group_id,
    ).filter(GroupMembership.user_id == user.id).all()]
    assigned_ids = set(direct_ids + group_ids)
    if not assigned_ids:
        return []
    return db.query(VMTemplate).filter(
        VMTemplate.id.in_(assigned_ids),
        VMTemplate.organization_id == organization_id,
        VMTemplate.enabled.is_(True),
    ).all()


def create_template(db: Session, payload, organization_id: int):
    t = VMTemplate(organization_id=organization_id, **payload.model_dump())
    db.add(t); db.commit(); db.refresh(t)
    return t


def patch_template(db: Session, id: int, payload, organization_id: int):
    t = db.query(VMTemplate).filter(VMTemplate.id == id, VMTemplate.organization_id == organization_id).first()
    if not t:
        raise HTTPException(status_code=404, detail='Template not found')
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(t, k, v)
    db.commit(); db.refresh(t)
    return t
