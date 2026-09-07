from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from app.core.config import settings
from app.workers.session_worker import run_once as session_run_once
from app.workers.cleanup_worker import run_once as cleanup_run_once
from app.workers.health_worker import run_once as health_run_once
from app.workers.reconciliation_worker import run_once as recon_run_once
from app.workers.update_worker import run_once as update_run_once

scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global scheduler
    if not settings.worker_scheduler_enabled:
        return
    if scheduler and scheduler.running:
        return
    scheduler = BackgroundScheduler()
    scheduler.add_job(session_run_once, 'interval', seconds=settings.session_cleanup_interval_seconds, id='session_cleanup', replace_existing=True, next_run_time=datetime.now(timezone.utc))
    scheduler.add_job(cleanup_run_once, 'interval', seconds=settings.session_cleanup_interval_seconds, id='cleanup', replace_existing=True, next_run_time=datetime.now(timezone.utc))
    scheduler.add_job(health_run_once, 'interval', seconds=settings.health_poll_interval_seconds, id='health', replace_existing=True, next_run_time=datetime.now(timezone.utc))
    scheduler.add_job(recon_run_once, 'interval', seconds=settings.reconciliation_interval_seconds, id='reconciliation', replace_existing=True, next_run_time=datetime.now(timezone.utc))
    scheduler.add_job(update_run_once, 'interval', seconds=settings.updater_poll_interval_seconds, id='deployment_updates', replace_existing=True)
    scheduler.start()


def stop_scheduler() -> None:
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
