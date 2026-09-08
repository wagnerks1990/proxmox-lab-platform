from app.main import app


def test_asset_routes_registered():
    paths = set(app.openapi()['paths'])
    assert '/api/admin/proxmox/assets/inventory' in paths
    assert '/api/admin/proxmox/assets/readiness' in paths
    assert '/api/admin/proxmox/assets/sync/iso' in paths
    assert '/api/admin/proxmox/assets/sync/ct-template' in paths
    assert '/api/admin/proxmox/assets/sync/vm-template' in paths
    assert '/api/admin/proxmox/assets/sync-jobs/{job_id}' in paths
