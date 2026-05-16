from app.services.session_service import SessionService
from app.db.session import SessionLocal
from app.core.config import settings
from app.workers.locks import acquire_worker_lock, release_worker_lock
from app.services.worker_run_service import WorkerRunService


def run_once() -> dict[str, int]:
    name = 'session_worker'
    if not acquire_worker_lock(name):
        return {'skipped_overlap': 1}
    db = SessionLocal()
    run = WorkerRunService(db).start(name)
    try:
        svc = SessionService(db)
        expired_idle = svc.expire_stale_sessions(settings.session_idle_timeout_seconds)
        expired_reconnect = svc.expire_reconnecting_sessions(settings.session_reconnect_timeout_seconds)
        failed_launching = svc.fail_stuck_launching(settings.heartbeat_timeout_seconds)
        out = {
            'expired_idle': expired_idle,
            'expired_reconnect': expired_reconnect,
            'failed_launching': failed_launching,
        }
        WorkerRunService(db).finish(run.id, 'success', out)
        return out
    finally:
        db.close()
        release_worker_lock(name)
