from app.architecture.state_machines import SessionState
from app.services.session_service import SessionService


class DummySession:
    def __init__(self):
        self.id = 1
        self.state = SessionState.DISCONNECTED.value
        self.last_heartbeat_at = None
        self.updated_at = None


class Q:
    def __init__(self, row): self.row = row
    def filter(self, *a, **k): return self
    def first(self): return self.row


class DB:
    def __init__(self, row): self.row=row
    def query(self, *a, **k): return Q(self.row)


def test_reconnect_success_path():
    row = DummySession()
    svc = SessionService(DB(row))
    out = svc.reconnect(1, 'reconnect-1')
    assert out is not None
