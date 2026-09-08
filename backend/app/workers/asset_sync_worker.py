import asyncio

from app.db.session import SessionLocal
from app.models.models import AssetSyncJob
from app.services.asset_sync import AssetSyncService


def run_once() -> dict[str, int]:
    db = SessionLocal()
    try:
        job = db.query(AssetSyncJob).filter(AssetSyncJob.state == 'queued').order_by(AssetSyncJob.id).with_for_update(skip_locked=True).first()
        if not job:
            return {'claimed': 0}
        job.state = 'running'
        job_id = job.id
        db.commit()
    finally:
        db.close()
    asyncio.run(AssetSyncService.process_job(job_id))
    return {'claimed': 1}
