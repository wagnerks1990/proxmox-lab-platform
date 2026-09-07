from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal
from app.services.deployment_updates import DeploymentUpdateService


def run_once() -> None:
    db = SessionLocal()
    try:
        service = DeploymentUpdateService(db)
        configured = service.get_settings()
        if not configured.automatic_updates:
            return
        now = datetime.now(timezone.utc)
        last = configured.last_checked_at
        if last is not None:
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if now - last < timedelta(minutes=configured.check_interval_minutes):
                return
        result = service.run('check', None)
        if result.get('ok') and result.get('update_available') and now.hour == configured.maintenance_hour_utc:
            service.run('apply', None)
    finally:
        db.close()
