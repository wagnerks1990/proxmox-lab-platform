from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import Class, Lab, LabAssignment, LabRun, StudentVM, User
from app.services.classroom_access import enforce_student_vm_operation
from app.services.organization_access import (
    OrganizationContext,
    organization_role_at_least,
)


def get_console_vm_for_user(
    db: Session,
    *,
    user: User,
    vm_id: int,
    organization: OrganizationContext,
    operation: str,
) -> StudentVM:
    """Return a VM only when the tenant role permits this console operation.

    Instructors are intentionally class-scoped. Organization owners/admins and a
    platform-admin break-glass context remain organization-wide.
    """
    query = db.query(StudentVM).filter(
        StudentVM.id == vm_id,
        StudentVM.organization_id == organization.id,
        StudentVM.deleted_at.is_(None),
    )
    if organization.role == "student":
        query = query.filter(StudentVM.owner_id == user.id)
    elif organization.role == "instructor":
        query = (
            query.join(
                LabAssignment,
                LabAssignment.student_vm_id == StudentVM.id,
            )
            .join(LabRun, LabRun.id == LabAssignment.lab_run_id)
            .join(Lab, Lab.id == LabRun.lab_id)
            .join(Class, Class.id == Lab.class_id)
            .filter(
                LabAssignment.organization_id == organization.id,
                LabRun.organization_id == organization.id,
                Lab.organization_id == organization.id,
                Class.organization_id == organization.id,
                Class.instructor_id == user.id,
            )
        )
    elif not organization_role_at_least(organization, "admin"):
        raise HTTPException(status_code=403, detail="A valid role is required")

    vm = query.first()
    if vm is None:
        raise HTTPException(status_code=404, detail="VM not found")
    if organization.role == "student":
        enforce_student_vm_operation(
            db,
            user_id=user.id,
            organization_id=organization.id,
            vm=vm,
            operation=operation,
        )
    return vm
