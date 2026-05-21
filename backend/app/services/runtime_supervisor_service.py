from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import WorkerRun


class RuntimeSupervisorService:
    def __init__(self, db: Session):
        self.db = db

    def summary(self) -> dict:
        db_status = 'ok'
        try:
            self.db.execute(text('SELECT 1'))
        except Exception:
            db_status = 'error'
        rows = self.db.query(WorkerRun).order_by(WorkerRun.started_at.desc()).limit(50).all()
        failed = sum(1 for r in rows if r.status == 'failed')
        stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
        stale = sum(1 for r in rows if r.status == 'running' and r.started_at and r.started_at < stale_cutoff)
        cleanup = next((r for r in rows if r.worker_name == 'session_worker'), None)
        cleanup_status = cleanup.status if cleanup else 'unknown'
        overall = 'healthy'
        if db_status == 'error' or failed > 3:
            overall = 'error'
        elif stale or failed:
            overall = 'warning'
        return {
            'scheduler_enabled': settings.worker_scheduler_enabled,
            'scheduler_running': self._scheduler_running(),
            'db_status': db_status,
            'telemetry_status': 'ok',
            'event_stream_status': 'memory',
            'recent_worker_failures': failed,
            'stale_worker_warnings': stale,
            'recent_session_cleanup_status': cleanup_status,
            'overall_status': overall,
        }

    def _scheduler_running(self) -> bool:
        try:
            from app.workers.scheduler import scheduler
            return bool(scheduler and scheduler.running)
        except Exception:
            return False
