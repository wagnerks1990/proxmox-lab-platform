from app.services.analytics_service import AnalyticsService


def test_analytics_summary_shape(monkeypatch):
    class Q:
        def __init__(self, rows=None, scalar_val=0):
            self.rows = rows or []
            self.s = scalar_val

        def group_by(self, *a, **k):
            return self

        def all(self):
            return self.rows

        def filter(self, *a, **k):
            return self

        def scalar(self):
            return self.s

    class DB:
        def query(self, *a, **k):
            return Q()

    out = AnalyticsService(DB()).summary()
    assert "sessions_by_state" in out and "active_sessions" in out
