from app.db.session import SessionLocal
from app.workers.locks import acquire_worker_lock, release_worker_lock
from app.services.worker_run_service import WorkerRunService


def run_once() -> dict[str, str]:
    name = "reconciliation_worker"
    if not acquire_worker_lock(name):
        return {'state': 'skipped_overlap'}
    db = SessionLocal()
    run = WorkerRunService(db).start(name)
    try:
        out = {'state': 'placeholder_safe'}
        WorkerRunService(db).finish(run.id, "success", out)
        return out
    finally:
        db.close()
        release_worker_lock(name)
