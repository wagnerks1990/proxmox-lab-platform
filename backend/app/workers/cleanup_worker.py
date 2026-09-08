from datetime import datetime

from app.db.session import SessionLocal
from app.models.models import LabAssignment
from app.services.operation_service import enqueue_operation
from app.workers.locks import acquire_worker_lock, release_worker_lock
from app.services.worker_run_service import WorkerRunService


def run_once() -> dict[str, int]:
    name = "cleanup_worker"
    if not acquire_worker_lock(name):
        return {'skipped_overlap': 1}
    db = SessionLocal()
    run = WorkerRunService(db).start(name)
    try:
        expired = db.query(LabAssignment).filter(
            LabAssignment.expires_at.is_not(None),
            LabAssignment.expires_at <= datetime.utcnow(),
            LabAssignment.student_vm_id.is_not(None),
            LabAssignment.status.in_(['assigned', 'ready', 'expired']),
        ).all()
        queued = 0
        for assignment in expired:
            assignment.status = 'expired'
            operation = enqueue_operation(
                db,
                organization_id=assignment.organization_id,
                requested_by=None,
                operation_type='vm.delete',
                target_type='student_vm',
                target_id=str(assignment.student_vm_id),
                payload={'expiration_cleanup': True, 'assignment_id': assignment.id},
                idempotency_key=f'assignment-expire:{assignment.id}:vm:{assignment.student_vm_id}',
            )
            queued += int(operation.state == 'queued')
        db.commit()
        out = {'expired_launch_artifacts_cleaned': 0, 'expired_vm_deletions_queued': queued}
        WorkerRunService(db).finish(run.id, "success", out)
        return out
    finally:
        db.close()
        release_worker_lock(name)
