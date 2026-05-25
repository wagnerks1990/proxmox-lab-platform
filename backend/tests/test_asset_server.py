from app.services.asset_server_control import AssetServerControl


class Obj:
    def __init__(self, **k): self.__dict__.update(k)


class Q:
    def __init__(self, rows): self.rows=rows
    def filter(self, *a, **k): return self
    def first(self): return self.rows[0] if self.rows else None
    def all(self): return self.rows


class DB:
    def __init__(self, m): self.m=m
    def query(self, model): return Q(self.m.get(model, []))


def test_kind_validation():
    from app.models.models import ProxmoxCluster
    db=DB({ProxmoxCluster:[Obj(id=1,is_active=True)]})
    s=AssetServerControl(db)
    try:
        s.status('bad')
        assert False
    except ValueError:
        assert True


def test_not_configured_when_runner_disabled(monkeypatch):
    from app.models.models import ProxmoxCluster, ProxmoxNode
    from app.services import asset_server_control as m
    monkeypatch.setattr(m.settings, 'host_runner_enabled', False)
    db=DB({ProxmoxCluster:[Obj(id=1,is_active=True)], ProxmoxNode:[Obj(cluster_id=1,node_name='pve-lab-01',status='online')]})
    out=AssetServerControl(db).status('iso')
    assert out['status']=='not_configured'
