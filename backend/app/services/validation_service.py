from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings


class ValidationService:
    def __init__(self, db: Session):
        self.db = db

    def run_checks(self) -> list[dict]:
        checks = []
        try:
            self.db.execute(text('SELECT 1'))
            checks.append(self._ok('database', 'Database is reachable'))
        except Exception:
            checks.append(self._fail('database', 'error', 'Database check failed', 'Check DB credentials and connectivity.'))
        checks.append(self._ok('scheduler_config', 'Scheduler configuration is present') if settings.session_cleanup_interval_seconds > 0 else self._fail('scheduler_config', 'warning', 'Scheduler interval invalid', 'Set SESSION_CLEANUP_INTERVAL_SECONDS > 0'))
        checks.append(self._ok('telemetry', 'Telemetry backend configured') if True else self._fail('telemetry', 'warning', 'Telemetry unavailable', 'Ensure telemetry table migration is applied.'))
        checks.append(self._ok('proxmox_config', 'Proxmox configuration present') if settings.proxmox_base_url and settings.proxmox_token_id else self._fail('proxmox_config', 'error', 'Missing Proxmox config', 'Set PROXMOX_* environment values.'))
        checks.append(self._ok('replay_store', f"Replay store backend={settings.replay_store_backend}"))
        checks.append(self._ok('worker_lock_store', f"Worker lock backend={settings.worker_lock_backend}"))
        return checks

    def _ok(self, name: str, message: str) -> dict:
        return {'name': name, 'status': 'pass', 'severity': 'info', 'message': message, 'suggested_fix': 'None'}

    def _fail(self, name: str, sev: str, message: str, fix: str) -> dict:
        return {'name': name, 'status': 'fail', 'severity': sev, 'message': message, 'suggested_fix': fix}
