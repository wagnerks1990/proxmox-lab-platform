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
