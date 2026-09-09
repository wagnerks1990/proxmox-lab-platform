from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import get_db
from redis import Redis

from app.core.config import settings
from app.workers import scheduler as scheduler_module

router = APIRouter()


@router.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is not ready") from exc
    if settings.worker_scheduler_enabled and not (
        scheduler_module.scheduler and scheduler_module.scheduler.running
    ):
        raise HTTPException(status_code=503, detail="Worker scheduler is not ready")
    if (
        settings.worker_lock_backend == "redis"
        or settings.replay_store_backend == "redis"
    ):
        try:
            Redis.from_url(settings.redis_url).ping()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Redis is not ready") from exc
    return {"ready": True}


@router.get("/health")
async def health():
    return {"status": "ok"}
