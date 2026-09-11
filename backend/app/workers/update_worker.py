from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal
from app.services.deployment_updates import DeploymentUpdateService


def should_check_for_update(now, last, interval_minutes, maintenance_hour_utc):
    if last is None:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    else:
        last = last.astimezone(timezone.utc)
    interval_elapsed = now - last >= timedelta(minutes=interval_minutes)
    maintenance_check_due = now.hour == maintenance_hour_utc and (
        last.date() != now.date() or last.hour != maintenance_hour_utc
    )
    return interval_elapsed or maintenance_check_due


def run_once() -> None:
    db = SessionLocal()
    try:
        service = DeploymentUpdateService(db)
        configured = service.get_settings()
        if not configured.automatic_updates:
            return
        now = datetime.now(timezone.utc)
        last = configured.last_checked_at
        if not should_check_for_update(
            now,
            last,
            configured.check_interval_minutes,
            configured.maintenance_hour_utc,
        ):
            return
        result = service.run("check", None)
        if (
            result.get("ok")
            and result.get("update_available")
            and now.hour == configured.maintenance_hour_utc
        ):
            service.run("apply", None, result.get("to_version"))
    finally:
        db.close()
