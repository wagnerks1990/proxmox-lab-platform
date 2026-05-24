import pytest
from app.services.asset_sync import AssetSyncService


class Obj:
    def __init__(self, **k): self.__dict__.update(k)


class DB:
    def __init__(self): self._id=1
    def add(self, obj):
        if not getattr(obj,'id',None): obj.id=self._id; self._id+=1
    def flush(self): pass
    def commit(self): pass


@pytest.mark.asyncio
async def test_url_safety_rejects_bad_scheme():
    s = AssetSyncService(DB())
    with pytest.raises(ValueError):
        await s.sync_iso('a.iso','local','ftp://10.0.16.126/a.iso',['pve-lab-01'])

@pytest.mark.asyncio
async def test_url_safety_rejects_credentials():
    s = AssetSyncService(DB())
    with pytest.raises(ValueError):
        await s.sync_iso('a.iso','local','http://u:p@10.0.16.126/a.iso',['pve-lab-01'])


@pytest.mark.asyncio
async def test_iso_idempotent_sets_finished_at(monkeypatch):
    s = AssetSyncService(DB())
    async def _ok(target_nodes, storage_id):
        return None
    monkeypatch.setattr(s, '_validate_targets', _ok)
    async def fake_discover(nodes, storage):
        return [{'node': nodes[0], 'items': [{'filename': 'virtio-win.iso'}]}]
    monkeypatch.setattr(s.assets, 'discover_isos_by_node', fake_discover)
    jobs = await s.sync_iso('virtio-win.iso', 'local', 'http://10.0.16.126/virtio-win.iso', ['pve-lab-02'])
    assert jobs[0].state == 'verified'
    assert jobs[0].finished_at is not None


@pytest.mark.asyncio
async def test_vm_sync_unsupported_sets_finished_at():
    s = AssetSyncService(DB())
    jobs = await s.sync_vm_template('pve-lab-01', 303, 'Ubuntu2604LTSv1c451c4', 'local-lvm', ['pve-lab-02'])
    assert jobs[0].state == 'failed'
    assert jobs[0].error
    assert jobs[0].finished_at is not None
