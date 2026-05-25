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
async def test_iso_download_polling_ok_then_verify(monkeypatch):
    s = AssetSyncService(DB())
    async def _nosleep(_secs):
        return None
    monkeypatch.setattr(s, '_sleep', _nosleep)
    async def _ok_targets(*_args, **_kwargs):
        return None
    monkeypatch.setattr(s, '_validate_targets', _ok_targets)

    async def discover_before(nodes, storage):
        # first call (pre-check) missing, second call (verify) present
        if not hasattr(discover_before, 'called'):
            discover_before.called = True
            return [{'node': nodes[0], 'items': []}]
        return [{'node': nodes[0], 'items': [{'filename': 'ubuntu.iso'}]}]

    async def dl(*_args, **_kwargs):
        return 'UPID:node:123'

    statuses = iter([{'status': 'running'}, {'status': 'stopped', 'exitstatus': 'OK'}])
    async def task_status(*_args, **_kwargs):
        return next(statuses)

    monkeypatch.setattr(s.assets, 'discover_isos_by_node', discover_before)
    monkeypatch.setattr(s.assets, 'download_url', dl)
    monkeypatch.setattr(s.assets, 'task_status', task_status)

    jobs = await s.sync_iso('ubuntu.iso', 'local', 'http://10.0.16.126/ubuntu.iso', ['pve-lab-02'])
    assert jobs[0].state == 'verified'
    assert jobs[0].proxmox_upid == 'UPID:node:123'
    assert jobs[0].finished_at is not None


@pytest.mark.asyncio
async def test_iso_download_task_failed(monkeypatch):
    s = AssetSyncService(DB())
    async def _nosleep(_secs):
        return None
    monkeypatch.setattr(s, '_sleep', _nosleep)
    async def _ok_targets(*_args, **_kwargs):
        return None
    monkeypatch.setattr(s, '_validate_targets', _ok_targets)
    async def _discover_empty(*_args, **_kwargs):
        return [{'node': 'pve-lab-02', 'items': []}]
    monkeypatch.setattr(s.assets, 'discover_isos_by_node', _discover_empty)
    async def _dl(*_args, **_kwargs):
        return 'UPID:node:124'
    monkeypatch.setattr(s.assets, 'download_url', _dl)
    async def _status(*_args, **_kwargs):
        return {'status': 'stopped', 'exitstatus': 'ERROR'}
    monkeypatch.setattr(s.assets, 'task_status', _status)

    jobs = await s.sync_iso('ubuntu.iso', 'local', 'http://10.0.16.126/ubuntu.iso', ['pve-lab-02'])
    assert jobs[0].state == 'failed'
    assert 'Proxmox task failed' in jobs[0].error
    assert jobs[0].finished_at is not None


@pytest.mark.asyncio
async def test_ct_download_ok_but_missing_verification(monkeypatch):
    s = AssetSyncService(DB())
    async def _nosleep(_secs):
        return None
    monkeypatch.setattr(s, '_sleep', _nosleep)
    async def _ok_targets(*_args, **_kwargs):
        return None
    monkeypatch.setattr(s, '_validate_targets', _ok_targets)
    async def _discover_empty(*_args, **_kwargs):
        return [{'node': 'pve-lab-03', 'items': []}]
    monkeypatch.setattr(s.assets, 'discover_ct_templates_by_node', _discover_empty)
    async def _dl(*_args, **_kwargs):
        return 'UPID:node:125'
    monkeypatch.setattr(s.assets, 'download_url', _dl)
    async def _status(*_args, **_kwargs):
        return {'status': 'stopped', 'exitstatus': 'OK'}
    monkeypatch.setattr(s.assets, 'task_status', _status)

    jobs = await s.sync_ct_template('debian.tar.zst', 'local', 'http://10.0.16.126/debian.tar.zst', ['pve-lab-03'])
    assert jobs[0].state == 'failed'
    assert 'Post-download verification failed' in jobs[0].error
    assert jobs[0].finished_at is not None


@pytest.mark.asyncio
async def test_vm_sync_unsupported_sets_finished_at():
    s = AssetSyncService(DB())
    jobs = await s.sync_vm_template('pve-lab-01', 303, 'Ubuntu2604LTSv1c451c4', 'local-lvm', ['pve-lab-02'])
    assert jobs[0].state == 'failed'
    assert jobs[0].error
    assert jobs[0].finished_at is not None
