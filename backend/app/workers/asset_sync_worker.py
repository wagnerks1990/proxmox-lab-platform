import asyncio
import socket
from datetime import datetime, timedelta

from sqlalchemy import or_

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import AssetSyncJob
from app.services.asset_sync import AssetSyncService


def run_once() -> dict[str, int]:
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        job = (
            db.query(AssetSyncJob)
            .filter(
                or_(
                    AssetSyncJob.state == "queued",
                    (AssetSyncJob.state.in_(["running", "syncing"]))
                    & or_(
                        AssetSyncJob.lease_expires_at.is_(None),
                        AssetSyncJob.lease_expires_at < now,
                    ),
                )
            )
            .order_by(AssetSyncJob.id)
            .with_for_update(skip_locked=True)
            .first()
        )
        if not job:
            return {"claimed": 0}
        job.state = "running"
        job.lease_owner = socket.gethostname()
        job.lease_expires_at = now + timedelta(
            seconds=settings.asset_sync_lease_seconds
        )
        job_id = job.id
        db.commit()
    finally:
        db.close()
    asyncio.run(AssetSyncService.process_job(job_id))
    return {"claimed": 1}
