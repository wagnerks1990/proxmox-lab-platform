import pytest
from app.api.routes import router
from app.api.routers import proxmox_assets


def test_source_url_route_registered():
    paths = {r.path for r in router.routes}
    assert '/api/admin/proxmox/assets/source-url' in paths


@pytest.mark.asyncio
async def test_source_url_missing_base(monkeypatch):
    monkeypatch.setattr(proxmox_assets.settings, 'asset_source_iso_base_url', None)
    out = await proxmox_assets.asset_source_url(kind='iso', filename='virtio-win.iso', _user=object())
    assert out['ok'] is False
    assert 'not configured' in out['message'].lower()


@pytest.mark.asyncio
async def test_source_url_with_base(monkeypatch):
    monkeypatch.setattr(proxmox_assets.settings, 'asset_source_iso_base_url', 'http://10.0.16.126:8088')
    out = await proxmox_assets.asset_source_url(kind='iso', filename='virtio-win.iso', _user=object())
    assert out['ok'] is True
    assert out['source_url'] == 'http://10.0.16.126:8088/virtio-win.iso'


@pytest.mark.asyncio
async def test_source_url_rejects_unsafe_filename(monkeypatch):
    monkeypatch.setattr(proxmox_assets.settings, 'asset_source_iso_base_url', 'http://10.0.16.126:8088')
    for bad in ['../evil.iso', 'path/file.iso', 'path\\file.iso', 'http://evil/file.iso']:
        with pytest.raises(Exception):
            await proxmox_assets.asset_source_url(kind='iso', filename=bad, _user=object())
