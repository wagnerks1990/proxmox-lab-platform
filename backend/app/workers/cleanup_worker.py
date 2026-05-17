from app.db.session import SessionLocal
from app.workers.locks import acquire_worker_lock, release_worker_lock
from app.services.worker_run_service import WorkerRunService


def run_once() -> dict[str, int]:
    name = "cleanup_worker"
    if not acquire_worker_lock(name):
        return {'skipped_overlap': 1}
    db = SessionLocal()
    run = WorkerRunService(db).start(name)
    try:
        out = {'expired_launch_artifacts_cleaned': 0}
        WorkerRunService(db).finish(run.id, "success", out)
        return out
    finally:
        db.close()
        release_worker_lock(name)
