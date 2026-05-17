from sqlalchemy import text, func
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.models import TelemetryEvent, VMSession, WorkerRun, DesktopPool
from app.architecture.state_machines import SessionState


class ValidationService:
    def __init__(self, db: Session):
        self.db = db

    def run_checks(self) -> list[dict]:
        checks = []
        checks.append(self._db_check())
        checks += [
            self._table_readable('telemetry_events', TelemetryEvent, 'telemetry'),
            self._table_readable('vm_sessions', VMSession, 'sessions'),
            self._table_readable('worker_runs', WorkerRun, 'workers'),
        ]
        checks.append(self._metric_check('stale_sessions', self.db.query(func.count(VMSession.id)).filter(VMSession.state == SessionState.EXPIRED.value).scalar() or 0, 'sessions'))
        checks.append(self._metric_check('failed_sessions', self.db.query(func.count(VMSession.id)).filter(VMSession.state == SessionState.FAILED.value).scalar() or 0, 'sessions'))
        checks.append(self._metric_check('active_sessions', self.db.query(func.count(VMSession.id)).filter(VMSession.state == SessionState.ACTIVE.value).scalar() or 0, 'sessions'))
        checks.append(self._metric_check('recent_worker_failure_count', self.db.query(func.count(WorkerRun.id)).filter(WorkerRun.status == 'failed').scalar() or 0, 'workers'))
        checks.append(self._ok('workers', 'scheduler_enabled', f'scheduler enabled={settings.worker_scheduler_enabled}'))
        checks.append(self._ok('telemetry', 'event_stream', 'event stream configured (in-process memory mode)'))
        checks.append(self._ok('security', 'replay_store_backend', f'replay backend={settings.replay_store_backend}'))
        checks.append(self._ok('security', 'worker_lock_backend', f'worker lock backend={settings.worker_lock_backend}'))
        checks.append(self._ok('pools', 'maintenance_pool_count', f"maintenance pools={self.db.query(func.count(DesktopPool.id)).filter(DesktopPool.maintenance_mode.is_(True)).scalar() or 0}"))
        weak = not settings.reconnect_token_secret
        checks.append(self._fail('security', 'reconnect_secret', 'warning', 'reconnect token secret falls back to jwt secret', 'Set RECONNECT_TOKEN_SECRET explicitly') if weak else self._ok('security', 'reconnect_secret', 'reconnect token secret configured'))
        return checks

    def _db_check(self):
        try:
            self.db.execute(text('SELECT 1'))
            return self._ok('database', 'connectivity', 'Database is reachable')
        except Exception:
            return self._fail('database', 'connectivity', 'error', 'Database check failed', 'Check DB credentials and connectivity.')

    def _table_readable(self, name, model, cat):
        try:
            self.db.query(func.count(model.id)).scalar()
            return self._ok(cat, name, f'{name} readable')
        except Exception:
            return self._fail(cat, name, 'error', f'{name} not readable', f'Apply migrations for {name}.')

    def _metric_check(self, name, value, cat):
        sev = 'warning' if value else 'info'
        status = 'fail' if value else 'pass'
        return {'category': cat, 'name': name, 'status': status, 'severity': sev, 'message': f'{name}={int(value)}', 'suggested_fix': 'Investigate if non-zero' if value else 'None', 'affected_resource': None}

    def _ok(self, cat, name, msg):
        return {'category': cat, 'name': name, 'status': 'pass', 'severity': 'info', 'message': msg, 'suggested_fix': 'None', 'affected_resource': None}

    def _fail(self, cat, name, sev, msg, fix):
        return {'category': cat, 'name': name, 'status': 'fail', 'severity': sev, 'message': msg, 'suggested_fix': fix, 'affected_resource': None}
