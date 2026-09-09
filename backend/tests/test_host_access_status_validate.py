from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_status_requires_active_cluster_when_missing():
    r = client.get("/api/admin/proxmox/host-access/status")
    assert r.status_code in (400, 401, 403)


def test_source_url_not_configured_response():
    r = client.get(
        "/api/admin/proxmox/assets/source-url?kind=iso&filename=virtio-win.iso"
    )
    assert r.status_code in (200, 401, 403)
    if r.status_code == 200:
        assert "ok" in r.json()
        if not r.json().get("ok"):
            assert "not configured" in (r.json().get("message") or "").lower()
