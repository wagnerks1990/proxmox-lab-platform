from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.config import settings
from app.api.routers.admin_proxmox_setup import patch_cluster
from app.middleware.csrf import CookieCsrfMiddleware, websocket_origin_allowed
from app.services.proxmox_bootstrap import ProxmoxBootstrapService
from app.services.proxmox_url import canonicalize_proxmox_api_url


@pytest.mark.parametrize(
    "value",
    [
        "http://pve.example.test:8006/api2/json",
        "https://user:pass@pve.example.test:8006/api2/json",
        "https://pve.example.test:8006/",
        "https://pve.example.test:8006/api2/json?next=evil",
        "https://pve.example.test:8006/api2/json#fragment",
    ],
)
def test_proxmox_url_rejects_noncanonical_destinations(value):
    with pytest.raises(ValueError):
        canonicalize_proxmox_api_url(value, verify_ssl=True)


def test_proxmox_url_canonicalizes_expected_api_path():
    assert (
        canonicalize_proxmox_api_url(
            "https://PVE.EXAMPLE.TEST:8006/api2/json/", verify_ssl=True
        )
        == "https://pve.example.test:8006/api2/json"
    )


def test_proxmox_tls_bypass_requires_explicit_host_policy(monkeypatch):
    monkeypatch.setattr(settings, "proxmox_allow_insecure_tls", False)
    with pytest.raises(ValueError, match="host policy"):
        canonicalize_proxmox_api_url(
            "https://pve.example.test:8006/api2/json", verify_ssl=False
        )


def test_generic_cluster_patch_cannot_retarget_stored_credentials():
    cluster = SimpleNamespace(
        id=1,
        api_url="https://pve.example.test:8006/api2/json",
        verify_ssl=True,
    )

    class Query:
        def filter(self, *_args):
            return self

        def first(self):
            return cluster

    db = SimpleNamespace(query=lambda _model: Query())
    with pytest.raises(HTTPException) as denied:
        patch_cluster(
            1,
            {"api_url": "https://attacker.example.test/api2/json"},
            _user=SimpleNamespace(id=1),
            db=db,
        )
    assert denied.value.status_code == 409
    assert cluster.api_url == "https://pve.example.test:8006/api2/json"


@pytest.mark.asyncio
async def test_manual_and_root_bootstrap_reject_url_before_network_access():
    service = ProxmoxBootstrapService(SimpleNamespace())
    with pytest.raises(ValueError, match="HTTPS"):
        await service.upsert_manual_token(
            {
                "name": "unsafe",
                "api_url": "http://attacker.example.test/api2/json",
                "token_user": "root@pam",
                "token_id": "test",
                "token_secret": "secret",
            }
        )
    with pytest.raises(ValueError, match="HTTPS"):
        await service.bootstrap_with_root(
            {
                "name": "unsafe",
                "api_url": "http://attacker.example.test/api2/json",
                "root_password": "secret",
            }
        )


def test_cookie_csrf_rejects_same_site_cross_origin_form(monkeypatch):
    monkeypatch.setattr(settings, "browser_trusted_origins", "")
    app = FastAPI()
    app.add_middleware(CookieCsrfMiddleware)

    @app.post("/mutate")
    def mutate():
        return {"ok": True}

    client = TestClient(app, base_url="https://lab.example.test")
    client.cookies.set(settings.auth_cookie_name, "session")
    response = client.post(
        "/mutate",
        headers={"Origin": "https://evil.example.test", "Sec-Fetch-Site": "same-site"},
    )
    assert response.status_code == 403


def test_cookie_csrf_allows_same_origin_browser_and_bearer_api(monkeypatch):
    monkeypatch.setattr(settings, "browser_trusted_origins", "")
    app = FastAPI()
    app.add_middleware(CookieCsrfMiddleware)

    @app.post("/mutate")
    def mutate():
        return {"ok": True}

    client = TestClient(app, base_url="https://lab.example.test")
    client.cookies.set(settings.auth_cookie_name, "session")
    assert (
        client.post(
            "/mutate",
            headers={
                "Origin": "https://lab.example.test",
                "Sec-Fetch-Site": "same-origin",
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/mutate", headers={"Authorization": "Bearer api-token"}
        ).status_code
        == 200
    )


def test_websocket_origin_validation_is_exact(monkeypatch):
    monkeypatch.setattr(settings, "browser_trusted_origins", "https://lab.example.test")
    trusted = SimpleNamespace(
        headers={"origin": "https://lab.example.test", "host": "lab.example.test"},
        url=SimpleNamespace(scheme="wss"),
    )
    sibling = SimpleNamespace(
        headers={"origin": "https://evil.example.test", "host": "lab.example.test"},
        url=SimpleNamespace(scheme="wss"),
    )
    assert websocket_origin_allowed(trusted)
    assert not websocket_origin_allowed(sibling)


def test_unsafe_dormant_connection_modules_are_absent():
    services = Path(__file__).parents[1] / "app" / "services"
    assert not (services / "protocol.py").exists()
    assert not (services / "connection_broker.py").exists()
    guacamole = (services / "guacamole.py").read_text()
    assert "authToken" not in guacamole
    assert "token=" not in guacamole
    assert "launch_url" not in guacamole


def test_ssh_terminal_defaults_fail_closed():
    from app.core.config import Settings

    assert Settings.model_fields["ssh_terminal_enabled"].default is False
