import asyncio
import json
import time
from collections.abc import Awaitable, Callable, Mapping
from urllib.parse import urlsplit

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings


LOCAL_HEALTH_PATHS = frozenset(
    {"/api/health", "/api/ready", "/v1/api/health", "/v1/api/ready"}
)
JWKS_REQUEST_TIMEOUT_SECONDS = 5.0
MAX_CACHED_KEYS = 32
UNKNOWN_KID_REFRESH_COOLDOWN_SECONDS = 30.0
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class CloudflareAccessInvalid(Exception):
    """The request did not carry a valid Cloudflare Access assertion."""


class CloudflareAccessUnavailable(Exception):
    """Cloudflare signing keys could not be refreshed safely."""


def _parse_host_header(value: str) -> tuple[str, int | None] | None:
    raw = value.strip()
    if not raw or raw != value or any(char in raw for char in "/@?#,\\"):
        return None
    try:
        parsed = urlsplit(f"//{raw}")
        port = parsed.port
    except ValueError:
        return None
    if parsed.username or parsed.password or not parsed.hostname:
        return None
    # urlsplit accepts some malformed unbracketed forms. Reconstruct the only
    # host shapes accepted by this boundary and compare them exactly.
    hostname = parsed.hostname.lower()
    rendered_host = f"[{hostname}]" if ":" in hostname else hostname
    rendered = f"{rendered_host}:{port}" if port is not None else rendered_host
    if rendered.lower() != raw.lower():
        return None
    return hostname, port


def cloudflare_tunnel_host_allowed(
    headers: Mapping[str, str], *, path: str | None = None
) -> bool:
    if not settings.cloudflare_tunnel_enabled:
        return True
    getlist = getattr(headers, "getlist", None)
    if callable(getlist) and len(getlist("host")) != 1:
        return False
    parsed = _parse_host_header(headers.get("host", ""))
    if parsed is None:
        return False
    hostname, port = parsed
    expected = settings.cloudflare_public_hostname.strip().lower()
    if hostname == expected and port in {None, 443}:
        return True
    return bool(path in LOCAL_HEALTH_PATHS and hostname in LOOPBACK_HOSTS)


def _issuer_for_team_domain(team_domain: str) -> str:
    value = team_domain.strip().rstrip("/")
    if "://" not in value:
        value = f"https://{value}"
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.lower().endswith(".cloudflareaccess.com")
        or parsed.hostname.lower() == "cloudflareaccess.com"
        or parsed.username
        or parsed.password
        or parsed.port is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "Cloudflare Access team domain must be an HTTPS "
            "*.cloudflareaccess.com origin"
        )
    return f"https://{parsed.hostname.lower()}"


JwksFetcher = Callable[[str], Awaitable[Mapping[str, object]]]


async def _fetch_jwks(url: str) -> Mapping[str, object]:
    try:
        async with httpx.AsyncClient(
            timeout=JWKS_REQUEST_TIMEOUT_SECONDS, follow_redirects=False
        ) as client:
            response = await client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        raise CloudflareAccessUnavailable from exc
    if not isinstance(payload, dict):
        raise CloudflareAccessUnavailable
    return payload


class CloudflareAccessVerifier:
    def __init__(
        self,
        *,
        team_domain: str,
        audience: str,
        jwks_ttl_seconds: int,
        jwks_fetcher: JwksFetcher | None = None,
    ):
        self.issuer = _issuer_for_team_domain(team_domain)
        self.audience = audience.strip()
        if not self.audience:
            raise ValueError("Cloudflare Access audience is required")
        self.jwks_url = f"{self.issuer}/cdn-cgi/access/certs"
        self.jwks_ttl_seconds = max(30, min(int(jwks_ttl_seconds), 86400))
        self._jwks_fetcher = jwks_fetcher or _fetch_jwks
        self._keys: dict[str, object] = {}
        self._expires_at = 0.0
        self._unknown_kid_refresh_after = 0.0
        self._refresh_lock = asyncio.Lock()

    async def _refresh_keys(self, *, unknown_kid: bool = False) -> bool:
        async with self._refresh_lock:
            now = time.monotonic()
            if unknown_kid:
                if now < self._unknown_kid_refresh_after:
                    return False
                # Set the global cooldown before network I/O. Concurrent
                # attacker-selected key IDs then share this one refresh even
                # if the JWKS request fails.
                self._unknown_kid_refresh_after = (
                    now + UNKNOWN_KID_REFRESH_COOLDOWN_SECONDS
                )
            elif self._keys and now < self._expires_at:
                return False
            payload = await self._jwks_fetcher(self.jwks_url)
            rows = payload.get("keys")
            if not isinstance(rows, list):
                raise CloudflareAccessUnavailable
            keys: dict[str, object] = {}
            try:
                for item in rows[:MAX_CACHED_KEYS]:
                    if not isinstance(item, dict):
                        continue
                    kid = item.get("kid")
                    if isinstance(kid, str) and kid and item.get("kty") == "RSA":
                        keys[kid] = RSAAlgorithm.from_jwk(item)
            except (TypeError, ValueError, jwt.PyJWTError) as exc:
                raise CloudflareAccessUnavailable from exc
            if not keys:
                raise CloudflareAccessUnavailable
            self._keys = keys
            self._expires_at = time.monotonic() + self.jwks_ttl_seconds
            return True

    async def verify(self, assertion: str | None) -> dict:
        if not assertion:
            raise CloudflareAccessInvalid
        try:
            header = jwt.get_unverified_header(assertion)
        except jwt.PyJWTError as exc:
            raise CloudflareAccessInvalid from exc
        kid = header.get("kid")
        if (
            header.get("alg") != "RS256"
            or not isinstance(kid, str)
            or not kid
            or len(kid) > 128
        ):
            raise CloudflareAccessInvalid

        cache_expired = not self._keys or time.monotonic() >= self._expires_at
        if cache_expired:
            await self._refresh_keys()
        key = self._keys.get(kid)
        if key is None:
            if cache_expired:
                # The just-fetched JWKS is authoritative. Do not immediately
                # fetch it a second time for the same unknown key ID.
                self._unknown_kid_refresh_after = max(
                    self._unknown_kid_refresh_after,
                    time.monotonic() + UNKNOWN_KID_REFRESH_COOLDOWN_SECONDS,
                )
            else:
                await self._refresh_keys(unknown_kid=True)
                key = self._keys.get(kid)
            if key is None:
                raise CloudflareAccessInvalid
        try:
            return jwt.decode(
                assertion,
                key=key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iss", "aud"]},
            )
        except jwt.PyJWTError as exc:
            raise CloudflareAccessInvalid from exc


_verifier: CloudflareAccessVerifier | None = None
_verifier_config: tuple[str, str, int] | None = None


def get_cloudflare_access_verifier() -> CloudflareAccessVerifier:
    global _verifier, _verifier_config
    config = (
        settings.cloudflare_access_team_domain,
        settings.cloudflare_access_audience,
        settings.cloudflare_access_jwks_ttl_seconds,
    )
    if _verifier is None or _verifier_config != config:
        _verifier = CloudflareAccessVerifier(
            team_domain=config[0], audience=config[1], jwks_ttl_seconds=config[2]
        )
        _verifier_config = config
    return _verifier


async def require_cloudflare_access(headers: Mapping[str, str]) -> None:
    if not settings.cloudflare_access_required:
        return
    verifier = get_cloudflare_access_verifier()
    await verifier.verify(headers.get("cf-access-jwt-assertion"))


class CloudflareAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not cloudflare_tunnel_host_allowed(request.headers, path=request.url.path):
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid Host header"},
                headers={"Cache-Control": "no-store"},
            )
        if request.url.path in LOCAL_HEALTH_PATHS:
            return await call_next(request)
        try:
            await require_cloudflare_access(request.headers)
        except CloudflareAccessInvalid:
            return JSONResponse(
                status_code=403,
                content={"detail": "Cloudflare Access authentication required"},
                headers={"Cache-Control": "no-store"},
            )
        except (CloudflareAccessUnavailable, ValueError):
            return JSONResponse(
                status_code=503,
                content={"detail": "Cloudflare Access validation unavailable"},
                headers={"Cache-Control": "no-store"},
            )
        return await call_next(request)
