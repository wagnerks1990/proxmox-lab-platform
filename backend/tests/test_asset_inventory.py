import pytest
from app.api.routers import proxmox_assets


class Obj:
    def __init__(self, **k): self.__dict__.update(k)


class Q:
    def __init__(self, rows): self.rows = rows
    def filter(self, *a, **k): return self
    def first(self): return self.rows[0] if self.rows else None


class DB:
    def __init__(self, active=True):
        from app.models.models import ProxmoxCluster
        self.map = {ProxmoxCluster: [Obj(id=1, is_active=active)] if active else []}
    def query(self, model): return Q(self.map.get(model, []))


@pytest.mark.asyncio
async def test_inventory_partial_errors(monkeypatch):
    async def nodes(self): return [{'node':'pve-lab-01','status':'online'},{'node':'pve-lab-02','status':'online'}]
    async def iso(self, n, s='local'):
        if n[0]=='pve-lab-02': raise RuntimeError('boom')
        return [{'node':'pve-lab-01','storage_id':'local','content_type':'iso','items':[{'volid':'local:iso/a.iso','filename':'a.iso','format':'iso','size':1}]}]
    async def ct(self, n, s='local'): return [{'node':n[0],'storage_id':'local','content_type':'vztmpl','items':[]}]
    async def vm(self, n): return [{'node':n[0],'templates':[{'vmid':303,'name':'Ubuntu','template':1,'status':'stopped'}]}]
    monkeypatch.setattr(proxmox_assets.ProxmoxAssetsService, 'discover_nodes', nodes)
    monkeypatch.setattr(proxmox_assets.ProxmoxAssetsService, 'discover_isos_by_node', iso)
    monkeypatch.setattr(proxmox_assets.ProxmoxAssetsService, 'discover_ct_templates_by_node', ct)
    monkeypatch.setattr(proxmox_assets.ProxmoxAssetsService, 'discover_vm_templates_by_node', vm)
    out = await proxmox_assets.assets_inventory(_user=Obj(), db=DB())
    assert 'errors_by_node' in out and 'pve-lab-02' in out['errors_by_node']
