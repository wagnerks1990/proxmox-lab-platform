from datetime import datetime, timedelta, timezone

from app.architecture.state_machines import SessionState
from app.models.models import VMSession
from app.services.session_service import SessionService


class Q:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self.rows


class DB:
    def __init__(self, rows):
        self.rows = rows

    def query(self, *_args, **_kwargs):
        return Q(self.rows)

    def commit(self):
        return None

    def rollback(self):
        return None


def test_expire_stale_sessions_marks_count():
    row = VMSession()
    row.state = SessionState.ACTIVE.value
    row.last_heartbeat_at = datetime.now(timezone.utc) - timedelta(hours=1)
    row.updated_at = datetime.now(timezone.utc)
    db = DB([row])
    svc = SessionService(db)
    assert svc.expire_stale_sessions(stale_seconds=10) == 1
