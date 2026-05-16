from app.services.reconciliation_planning_service import ReconciliationPlanningService


def test_preview_shape(monkeypatch):
    class Q:
        def __init__(self, items): self.items=items
        def count(self): return len(self.items)
        def all(self): return self.items
        def filter(self, *a, **k): return self
    class Pool:
        enabled=True; maintenance_mode=False; desired_size=1
        __dict__={'enabled':True,'maintenance_mode':False,'desired_size':1,'pool_type':'persistent','default_protocol':'SSH_WS'}
    class DB:
        def query(self, model):
            n = getattr(model, '__name__', '')
            if n=='DesktopPool': return Q([Pool()])
            return Q([])
    out = ReconciliationPlanningService(DB()).preview()
    assert 'proposed_actions' in out
