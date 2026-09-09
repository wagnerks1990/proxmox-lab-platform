from sqlalchemy import text

from app.db.session import SessionLocal
from app.workers.locks import acquire_worker_lock, release_worker_lock
from app.services.worker_run_service import WorkerRunService


def run_once() -> dict[str, str]:
    name = "health_worker"
    if not acquire_worker_lock(name):
        return {"state": "skipped_overlap"}
    db = SessionLocal()
    run = WorkerRunService(db).start(name)
    try:
        db.execute(text("SELECT 1"))
        out = {"database": "ok", "proxmox": "unknown", "guacamole": "unknown"}
        WorkerRunService(db).finish(run.id, "success", out)
        return out
    except Exception as exc:
        out = {"database": "error", "proxmox": "unknown", "guacamole": "unknown"}
        WorkerRunService(db).finish(run.id, "failed", out, str(exc))
        return out
    finally:
        db.close()
        release_worker_lock(name)
