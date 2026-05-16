from app.services.session_service import SessionService
from app.db.session import SessionLocal
from app.core.config import settings


def run_once() -> dict[str, int]:
    db = SessionLocal()
    try:
        svc = SessionService(db)
        expired = svc.expire_stale_sessions(settings.session_idle_timeout_seconds)
        return {'expired_sessions': expired}
    finally:
        db.close()
