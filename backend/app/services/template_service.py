from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.models import LabAssignment, LabRun, VMTemplate
from app.services.classroom_access import assignment_effectively_open


def list_templates(db: Session, user, organization_id: int, organization_role: str):
    if organization_role in {"instructor", "admin", "owner"}:
        return (
            db.query(VMTemplate)
            .filter(VMTemplate.organization_id == organization_id)
            .all()
        )
    assignments = (
        db.query(LabAssignment)
        .filter(
            LabAssignment.organization_id == organization_id,
            LabAssignment.user_id == user.id,
            LabAssignment.status.in_(["assigned", "ready"]),
        )
        .all()
    )
    assigned_ids = set()
    for assignment in assignments:
        run = (
            db.query(LabRun)
            .filter(
                LabRun.id == assignment.lab_run_id,
                LabRun.organization_id == organization_id,
            )
            .first()
        )
        if run and assignment_effectively_open(assignment, run):
            assigned_ids.add(assignment.template_id)
    if not assigned_ids:
        return []
    return (
        db.query(VMTemplate)
        .filter(
            VMTemplate.id.in_(assigned_ids),
            VMTemplate.organization_id == organization_id,
            VMTemplate.enabled.is_(True),
        )
        .all()
    )


def create_template(db: Session, payload, organization_id: int):
    t = VMTemplate(organization_id=organization_id, **payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def patch_template(db: Session, id: int, payload, organization_id: int):
    t = (
        db.query(VMTemplate)
        .filter(VMTemplate.id == id, VMTemplate.organization_id == organization_id)
        .first()
    )
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t
