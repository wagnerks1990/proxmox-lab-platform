import asyncio
import time
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from app.api.routers import console_ws
from app.core.config import Settings, settings
from app.security.cloudflare_access import (
    CloudflareAccessInvalid,
    CloudflareAccessMiddleware,
    CloudflareAccessUnavailable,
    CloudflareAccessVerifier,
)


TEAM_DOMAIN = "labgoblin.cloudflareaccess.com"
ISSUER = f"https://{TEAM_DOMAIN}"
AUDIENCE = "access-audience"
KID = "test-key"


def _settings_kwargs():
    return {
        "database_url": "sqlite+pysqlite:///:memory:",
        "jwt_secret_key": "test-jwt-secret-test-jwt-secret-1234",
        "proxmox_base_url": "https://127.0.0.1:8006/api2/json",
        "proxmox_token_id": "ci@pve!labgoblin",
        "proxmox_token_secret": "test-proxmox-secret",
    }


@pytest.mark.parametrize(
    "hostname",
    ["", "localhost", "127.0.0.1", "https://lab.example.edu", "lab_example.edu"],
)
def test_enabled_tunnel_rejects_missing_or_invalid_public_hostname(hostname):
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            cloudflare_tunnel_enabled=True,
            cloudflare_public_hostname=hostname,
            **_settings_kwargs(),
        )


def test_enabled_tunnel_normalizes_public_hostname():
    configured = Settings(
        _env_file=None,
        cloudflare_tunnel_enabled=True,
        cloudflare_public_hostname="LAB.Example.EDU",
        **_settings_kwargs(),
    )
    assert configured.cloudflare_public_hostname == "lab.example.edu"


@pytest.mark.parametrize(
    "team_domain",
    [
        "http://labgoblin.cloudflareaccess.com",
        "https://example.test",
        "https://labgoblin.cloudflareaccess.com.evil.test",
        "https://localhost",
        "https://127.0.0.1",
        "https://user:pass@labgoblin.cloudflareaccess.com",
        "https://labgoblin.cloudflareaccess.com/path",
    ],
)
def test_team_domain_rejects_non_cloudflare_or_non_origin_values(team_domain):
    with pytest.raises(ValueError):
        CloudflareAccessVerifier(
            team_domain=team_domain,
            audience=AUDIENCE,
            jwks_ttl_seconds=300,
        )


def _key_material(kid=KID):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    public_jwk.update({"kid": kid, "alg": "RS256", "use": "sig"})
    return private_key, {"keys": [public_jwk]}


def _token(private_key, *, kid=KID, **overrides):
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "access-user",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": now + timedelta(minutes=5),
        **overrides,
    }
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": kid})


@pytest.mark.asyncio
async def test_verifier_accepts_only_signed_exact_issuer_and_audience():
    private_key, jwks = _key_material()

    async def fetcher(url):
        assert url == f"{ISSUER}/cdn-cgi/access/certs"
        return jwks

    verifier = CloudflareAccessVerifier(
        team_domain=TEAM_DOMAIN,
        audience=AUDIENCE,
        jwks_ttl_seconds=300,
        jwks_fetcher=fetcher,
    )
    assert (await verifier.verify(_token(private_key)))["sub"] == "access-user"

    for token in (
        _token(private_key, iss="https://other.cloudflareaccess.com"),
        _token(private_key, aud="other-audience"),
        _token(private_key, exp=datetime.now(timezone.utc) - timedelta(seconds=1)),
    ):
        with pytest.raises(CloudflareAccessInvalid):
            await verifier.verify(token)


@pytest.mark.asyncio
async def test_cached_key_survives_outage_but_expired_cache_fails_closed():
    private_key, jwks = _key_material()
    calls = 0

    async def fetcher(_url):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise CloudflareAccessUnavailable
        return jwks

    verifier = CloudflareAccessVerifier(
        team_domain=TEAM_DOMAIN,
        audience=AUDIENCE,
        jwks_ttl_seconds=30,
        jwks_fetcher=fetcher,
    )
    token = _token(private_key)
    await verifier.verify(token)
    await verifier.verify(token)
    assert calls == 1
    verifier._expires_at = time.monotonic() - 1
    with pytest.raises(CloudflareAccessUnavailable):
        await verifier.verify(token)


@pytest.mark.asyncio
async def test_unknown_rotated_key_forces_one_refresh_and_is_accepted():
    old_private_key, old_jwks = _key_material("old-key")
    rotated_private_key, rotated_jwks = _key_material("rotated-key")
    responses = [old_jwks, rotated_jwks]
    calls = 0

    async def fetcher(_url):
        nonlocal calls
        response = responses[min(calls, len(responses) - 1)]
        calls += 1
        return response

    verifier = CloudflareAccessVerifier(
        team_domain=TEAM_DOMAIN,
        audience=AUDIENCE,
        jwks_ttl_seconds=300,
        jwks_fetcher=fetcher,
    )
    await verifier.verify(_token(old_private_key, kid="old-key"))
    claims = await verifier.verify(_token(rotated_private_key, kid="rotated-key"))

    assert claims["sub"] == "access-user"
    assert calls == 2


@pytest.mark.asyncio
async def test_concurrent_unknown_kids_singleflight_and_obey_global_cooldown():
    known_private_key, known_jwks = _key_material("known-key")
    unknown_private_key, _ = _key_material("unknown-key")
    calls = 0

    async def fetcher(_url):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return known_jwks

    verifier = CloudflareAccessVerifier(
        team_domain=TEAM_DOMAIN,
        audience=AUDIENCE,
        jwks_ttl_seconds=300,
        jwks_fetcher=fetcher,
    )
    await verifier.verify(_token(known_private_key, kid="known-key"))
    tokens = [_token(unknown_private_key, kid=f"unknown-{index}") for index in range(8)]

    results = await asyncio.gather(
        *(verifier.verify(token) for token in tokens), return_exceptions=True
    )
    assert all(isinstance(result, CloudflareAccessInvalid) for result in results)
    assert calls == 2

    with pytest.raises(CloudflareAccessInvalid):
        await verifier.verify(_token(unknown_private_key, kid="another-unknown"))
    assert calls == 2

    verifier._unknown_kid_refresh_after = time.monotonic() - 1
    with pytest.raises(CloudflareAccessInvalid):
        await verifier.verify(_token(unknown_private_key, kid="after-cooldown"))
    assert calls == 3


@pytest.mark.asyncio
async def test_failed_unknown_kid_refresh_keeps_fresh_known_key_without_refetch():
    known_private_key, known_jwks = _key_material("known-key")
    unknown_private_key, _ = _key_material("unknown-key")
    calls = 0

    async def fetcher(_url):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise CloudflareAccessUnavailable
        return known_jwks

    verifier = CloudflareAccessVerifier(
        team_domain=TEAM_DOMAIN,
        audience=AUDIENCE,
        jwks_ttl_seconds=300,
        jwks_fetcher=fetcher,
    )
    known_token = _token(known_private_key, kid="known-key")
    await verifier.verify(known_token)

    with pytest.raises(CloudflareAccessUnavailable):
        await verifier.verify(_token(unknown_private_key, kid="unknown-key"))
    with pytest.raises(CloudflareAccessInvalid):
        await verifier.verify(_token(unknown_private_key, kid="other-unknown"))
    assert calls == 2
    assert (await verifier.verify(known_token))["sub"] == "access-user"
    assert calls == 2


def test_required_middleware_denies_missing_assertion_but_bypasses_health(monkeypatch):
    monkeypatch.setattr(settings, "cloudflare_access_required", True)
    monkeypatch.setattr(settings, "cloudflare_access_team_domain", TEAM_DOMAIN)
    monkeypatch.setattr(settings, "cloudflare_access_audience", AUDIENCE)
    app = FastAPI()
    app.add_middleware(CloudflareAccessMiddleware)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/ready")
    def ready():
        return {"ready": True}

    @app.get("/api/private")
    def private():
        return {"unexpected": True}

    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/ready").status_code == 200
        response = client.get("/api/private")
        assert response.status_code == 403
        assert response.headers["cache-control"] == "no-store"


def test_required_middleware_returns_503_when_expired_keys_cannot_refresh(
    monkeypatch,
):
    class UnavailableVerifier:
        async def verify(self, _assertion):
            raise CloudflareAccessUnavailable

    monkeypatch.setattr(settings, "cloudflare_access_required", True)
    monkeypatch.setattr(
        "app.security.cloudflare_access.get_cloudflare_access_verifier",
        lambda: UnavailableVerifier(),
    )
    app = FastAPI()
    app.add_middleware(CloudflareAccessMiddleware)

    @app.get("/api/private")
    def private():
        return {"unexpected": True}

    with TestClient(app) as client:
        response = client.get(
            "/api/private", headers={"Cf-Access-Jwt-Assertion": "expired-cache"}
        )
        assert response.status_code == 503
        assert response.headers["cache-control"] == "no-store"


def test_tunnel_host_boundary_is_exact_and_health_allows_only_loopback(monkeypatch):
    monkeypatch.setattr(settings, "cloudflare_tunnel_enabled", True)
    monkeypatch.setattr(settings, "cloudflare_public_hostname", "lab.example.edu")
    monkeypatch.setattr(settings, "cloudflare_access_required", False)
    app = FastAPI()
    app.add_middleware(CloudflareAccessMiddleware)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/private")
    def private():
        return {"ok": True}

    with TestClient(app, base_url="https://lab.example.edu") as client:
        assert client.get("/api/private").status_code == 200
        assert (
            client.get(
                "/api/private", headers={"Host": "lab.example.edu:443"}
            ).status_code
            == 200
        )
        for host in (
            "evil.example.edu",
            "lab.example.edu:80",
            "user@lab.example.edu",
            "lab.example.edu.evil.test",
            "lab.example.edu,evil.test",
        ):
            response = client.get("/api/private", headers={"Host": host})
            assert response.status_code == 400
            assert response.headers["cache-control"] == "no-store"
        for host in ("localhost:8080", "127.0.0.1:8080", "[::1]:8080"):
            assert client.get("/api/health", headers={"Host": host}).status_code == 200
            assert client.get("/api/private", headers={"Host": host}).status_code == 400


class _DeniedWebSocket:
    headers = {}
    cookies = {}
    query_params = {}

    def __init__(self):
        self.closed = None

    async def close(self, *, code, reason):
        self.closed = (code, reason)


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", [console_ws.ssh_ws, console_ws.novnc_ws])
async def test_console_websockets_apply_access_before_application_auth(
    monkeypatch, handler
):
    monkeypatch.setattr(settings, "cloudflare_access_required", True)
    monkeypatch.setattr(settings, "cloudflare_access_team_domain", TEAM_DOMAIN)
    monkeypatch.setattr(settings, "cloudflare_access_audience", AUDIENCE)
    websocket = _DeniedWebSocket()

    await handler(1, websocket, db=None)

    assert websocket.closed == (1008, "Cloudflare Access required")


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", [console_ws.ssh_ws, console_ws.novnc_ws])
async def test_console_websockets_reject_host_before_access_or_session(
    monkeypatch, handler
):
    monkeypatch.setattr(settings, "cloudflare_tunnel_enabled", True)
    monkeypatch.setattr(settings, "cloudflare_public_hostname", "lab.example.edu")
    monkeypatch.setattr(settings, "cloudflare_access_required", False)
    websocket = _DeniedWebSocket()
    websocket.headers = {"host": "evil.example.edu"}

    await handler(1, websocket, db=None)

    assert websocket.closed == (1008, "Invalid Host header")
