from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import Enrollment, Lab, LabAssignment, LabRun, StudentVM


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def as_utc_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def run_effectively_open(run: LabRun, now: datetime | None = None) -> bool:
    current = as_utc_naive(now) or utcnow()
    if run.state not in {"scheduled", "active"}:
        return False
    starts_at = as_utc_naive(run.starts_at)
    ends_at = as_utc_naive(run.ends_at)
    if starts_at and current < starts_at:
        return False
    if ends_at and current >= ends_at:
        return False
    return True


def assignment_effectively_open(
    assignment: LabAssignment, run: LabRun, now: datetime | None = None
) -> bool:
    current = now or utcnow()
    return (
        assignment.status in {"assigned", "ready"}
        and (not assignment.expires_at or current < as_utc_naive(assignment.expires_at))
        and run_effectively_open(run, current)
    )


def assignment_for_provisioning(
    db: Session,
    *,
    assignment_id: int | None,
    user_id: int,
    organization_id: int,
    template_id: int,
) -> tuple[LabAssignment, LabRun]:
    if assignment_id is None:
        raise HTTPException(
            status_code=403, detail="An active classroom assignment is required"
        )
    assignment = (
        db.query(LabAssignment)
        .filter(
            LabAssignment.id == assignment_id,
            LabAssignment.organization_id == organization_id,
            LabAssignment.user_id == user_id,
        )
        .with_for_update()
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Classroom assignment not found")
    run = (
        db.query(LabRun)
        .filter(
            LabRun.id == assignment.lab_run_id,
            LabRun.organization_id == organization_id,
        )
        .first()
    )
    if not run or not assignment_effectively_open(assignment, run):
        raise HTTPException(
            status_code=403, detail="Classroom assignment is not currently active"
        )
    lab = (
        db.query(Lab)
        .filter(Lab.id == run.lab_id, Lab.organization_id == organization_id)
        .first()
    )
    if (
        not lab
        or not db.query(Enrollment)
        .filter(
            Enrollment.class_id == lab.class_id,
            Enrollment.user_id == user_id,
            Enrollment.is_active.is_(True),
        )
        .first()
    ):
        raise HTTPException(
            status_code=403, detail="An active class enrollment is required"
        )
    if assignment.template_id != template_id:
        raise HTTPException(
            status_code=422, detail="Template does not match the classroom assignment"
        )
    if assignment.student_vm_id is not None or assignment.status == "ready":
        raise HTTPException(
            status_code=409, detail="Classroom assignment already has a VM"
        )
    return assignment, run


def active_assignment_for_vm(
    db: Session, *, user_id: int, organization_id: int, vm_id: int
) -> tuple[LabAssignment, LabRun, Lab] | None:
    assignment = (
        db.query(LabAssignment)
        .filter(
            LabAssignment.organization_id == organization_id,
            LabAssignment.user_id == user_id,
            LabAssignment.student_vm_id == vm_id,
        )
        .first()
    )
    if not assignment:
        return None
    run = (
        db.query(LabRun)
        .filter(
            LabRun.id == assignment.lab_run_id,
            LabRun.organization_id == organization_id,
        )
        .first()
    )
    if not run or not assignment_effectively_open(assignment, run):
        return None
    lab = (
        db.query(Lab)
        .filter(Lab.id == run.lab_id, Lab.organization_id == organization_id)
        .first()
    )
    if (
        not lab
        or not db.query(Enrollment)
        .filter(
            Enrollment.class_id == lab.class_id,
            Enrollment.user_id == user_id,
            Enrollment.is_active.is_(True),
        )
        .first()
    ):
        return None
    return assignment, run, lab


def enforce_student_vm_operation(
    db: Session, *, user_id: int, organization_id: int, vm: StudentVM, operation: str
):
    access = active_assignment_for_vm(
        db, user_id=user_id, organization_id=organization_id, vm_id=vm.id
    )
    if not access:
        raise HTTPException(
            status_code=403,
            detail="VM is not available through an active classroom assignment",
        )
    _assignment, _run, lab = access
    if operation in {"delete", "remove"}:
        raise HTTPException(
            status_code=403,
            detail="Assigned classroom VMs are managed by the instructor",
        )
    if operation == "stop" and not lab.student_can_power_off:
        raise HTTPException(
            status_code=403, detail="Students may not power off this lab VM"
        )
    if operation in {"reboot", "reset"} and not lab.student_can_reset:
        raise HTTPException(
            status_code=403, detail="Students may not reset this lab VM"
        )
    if operation == "terminal" and not lab.terminal_enabled:
        raise HTTPException(
            status_code=403, detail="Terminal access is disabled for this lab"
        )
    if operation in {"console", "spice"} and not lab.console_enabled:
        raise HTTPException(
            status_code=403, detail="Console access is disabled for this lab"
        )
    if operation == "rdp" and not lab.rdp_enabled:
        raise HTTPException(
            status_code=403, detail="RDP access is disabled for this lab"
        )
    return access
