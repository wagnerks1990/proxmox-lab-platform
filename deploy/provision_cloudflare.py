#!/usr/bin/env python3
"""Provision LabGoblin's dedicated Cloudflare Tunnel and Access boundary.

This is a host-only bootstrap tool. It deliberately uses only the Python
standard library, reads the Cloudflare API token from a protected file, and
never prints either the API token or the remotely-managed Tunnel token.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import datetime as dt
import json
import os
from pathlib import Path
import re
import random
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
import uuid


API_ORIGIN = "https://api.cloudflare.com"
STATE_VERSION = 1
DEFAULT_STATE = Path("/etc/labgoblin/cloudflare-provision.json")
DEFAULT_TOKEN_DEST = Path("/etc/labgoblin/cloudflare-tunnel-token")
HOST_RE = re.compile(
    r"^(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)
TEAM_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.cloudflareaccess\.com$")
ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
TUNNEL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


class ProvisionError(RuntimeError):
    """A safe, user-facing provisioning failure."""


class ApiError(ProvisionError):
    pass


class AmbiguousPostError(ApiError):
    """A POST may have reached Cloudflare but no response was received."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        raise ApiError(f"Cloudflare API unexpectedly returned redirect HTTP {code}")


class CloudflareAPI:
    """Small Cloudflare v4 API client with intentionally non-verbose errors."""

    def __init__(self, token: str, *, timeout: float = 15.0):
        self._token = token
        self.timeout = timeout
        self._opener = urllib.request.build_opener(_NoRedirect())

    def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Cloudflare API path must be absolute")
        url = f"{API_ORIGIN}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = None
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "User-Agent": "LabGoblin-Cloudflare-Provision/1",
        }
        if body is not None:
            data = json.dumps(body, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        retryable_method = method in {"GET", "PUT", "PATCH", "DELETE"}
        raw = b""
        response = None
        for attempt in range(3):
            request = urllib.request.Request(
                url, data=data, headers=headers, method=method
            )
            try:
                with self._opener.open(request, timeout=self.timeout) as response:
                    raw = response.read(2 * 1024 * 1024 + 1)
                break
            except urllib.error.HTTPError as exc:
                raw = exc.read(256 * 1024)
                if (
                    retryable_method
                    and attempt < 2
                    and (exc.code == 429 or 500 <= exc.code <= 599)
                ):
                    self._wait_before_retry(attempt, exc.headers.get("Retry-After"))
                    continue
                raise self._api_error(exc.code, raw) from None
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if retryable_method and attempt < 2:
                    self._wait_before_retry(attempt, None)
                    continue
                advice = (
                    "; rerun plan, inspect any exact match, then use "
                    "--adopt-existing only if it is the intended dedicated resource"
                    if method == "POST"
                    else ""
                )
                # Never include request headers, payloads, or response bodies here.
                error_type = AmbiguousPostError if method == "POST" else ApiError
                raise error_type(
                    f"Cloudflare API connection failed: {type(exc).__name__}{advice}"
                ) from None
        if len(raw) > 2 * 1024 * 1024:
            raise ApiError("Cloudflare API response exceeded the safety limit")
        try:
            envelope = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError("Cloudflare API returned an invalid JSON response") from None
        if not isinstance(envelope, dict) or envelope.get("success") is not True:
            raise self._api_error(getattr(response, "status", 0), raw)
        return envelope.get("result")

    @staticmethod
    def _wait_before_retry(attempt: int, retry_after: str | None) -> None:
        delay = min(8.0, 0.5 * (2**attempt))
        if retry_after:
            try:
                delay = min(10.0, max(delay, float(retry_after)))
            except ValueError:
                pass
        time.sleep(delay + random.uniform(0.0, 0.25))

    def _api_error(self, status_code: int, raw: bytes) -> ApiError:
        messages: list[str] = []
        try:
            envelope = json.loads(raw)
            for item in envelope.get("errors", []):
                if not isinstance(item, dict):
                    continue
                code = item.get("code")
                message = str(item.get("message", "Cloudflare API error"))[:300]
                message = message.replace(self._token, "[REDACTED]")
                messages.append(f"{code}: {message}" if code is not None else message)
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            pass
        detail = "; ".join(messages) if messages else "request failed"
        return ApiError(f"Cloudflare API HTTP {status_code}: {detail}")


@dataclass(frozen=True)
class Desired:
    account_id: str
    zone_name: str
    hostname: str
    access_selector_kind: str
    access_selector_value: str
    team_domain: str
    tunnel_name: str
    access_app_name: str
    access_policy_name: str
    session_duration: str


@dataclass
class OwnedState:
    schema_version: int
    managed_by: str
    account_id: str
    zone_id: str
    zone_name: str
    hostname: str
    access_selector_kind: str
    access_selector_value: str
    team_domain: str
    tunnel_id: str
    tunnel_name: str
    access_app_id: str
    access_app_name: str
    access_audience: str
    access_policy_id: str
    access_policy_name: str
    dns_record_id: str
    updated_at: str


@dataclass
class Discovery:
    zone_id: str
    tunnel: dict[str, Any] | None
    tunnel_config: dict[str, Any] | None
    policy: dict[str, Any] | None
    app: dict[str, Any] | None
    dns: dict[str, Any] | None
    state: OwnedState | None


@dataclass(frozen=True)
class Change:
    action: str
    resource: str
    detail: str


def _validate_hostname(value: str, label: str) -> str:
    value = value.strip().lower().rstrip(".")
    if not HOST_RE.fullmatch(value):
        raise ProvisionError(f"{label} must be a valid fully qualified DNS hostname")
    return value


def _validate_identifier(value: str, label: str) -> str:
    if not ID_RE.fullmatch(value):
        raise ProvisionError(f"{label} is not a valid Cloudflare identifier")
    return value


def _validate_resource_identifier(value: Any, label: str) -> str:
    normalized = str(value)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", normalized):
        raise ApiError(f"Cloudflare returned an invalid {label} ID")
    return normalized


def desired_from_args(args: argparse.Namespace) -> Desired:
    hostname = _validate_hostname(args.hostname, "--hostname")
    zone = _validate_hostname(args.zone, "--zone")
    if hostname == zone or not hostname.endswith(f".{zone}"):
        raise ProvisionError("--hostname must be a subdomain of --zone")
    if args.access_group_id:
        try:
            selector_value = str(uuid.UUID(args.access_group_id))
        except (AttributeError, ValueError):
            raise ProvisionError("--access-group-id must be a UUID") from None
        selector_kind = "group"
        policy_subject = f"Access group {selector_value}"
    else:
        selector_value = _validate_hostname(
            args.allow_email_domain, "--allow-email-domain"
        )
        selector_kind = "email_domain"
        policy_subject = selector_value
    team_domain = args.team_domain.strip().lower().rstrip(".")
    if not TEAM_RE.fullmatch(team_domain):
        raise ProvisionError("--team-domain must be <team>.cloudflareaccess.com")
    account_id = _validate_identifier(args.account_id, "--account-id")
    if len(args.session_duration) > 32 or not re.fullmatch(
        r"(?:[1-9][0-9]*[smh])+", args.session_duration
    ):
        raise ProvisionError(
            "--session-duration must use Cloudflare units, such as 12h"
        )
    slug = re.sub(r"[^a-z0-9-]+", "-", hostname.replace(".", "-"))[:72].strip("-")
    tunnel_name = args.tunnel_name or f"labgoblin-{slug}"
    if not TUNNEL_NAME_RE.fullmatch(tunnel_name):
        raise ProvisionError(
            "--tunnel-name must contain 1-100 letters, digits, dots, underscores, or hyphens"
        )
    return Desired(
        account_id=account_id,
        zone_name=zone,
        hostname=hostname,
        access_selector_kind=selector_kind,
        access_selector_value=selector_value,
        team_domain=team_domain,
        tunnel_name=tunnel_name,
        access_app_name=f"LabGoblin — {hostname}",
        access_policy_name=f"LabGoblin — allow {policy_subject}",
        session_duration=args.session_duration,
    )


def read_protected_secret(path: Path) -> str:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ProvisionError(
            f"Unable to open protected API token file: {exc.strerror}"
        ) from None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ProvisionError("API token path must be a regular file")
        if info.st_uid != os.geteuid():
            raise ProvisionError("API token file must be owned by the invoking user")
        if stat.S_IMODE(info.st_mode) & 0o077:
            raise ProvisionError(
                "API token file must not be accessible by group or others"
            )
        raw = os.read(fd, 8193)
    finally:
        os.close(fd)
    if len(raw) > 8192:
        raise ProvisionError("API token is unexpectedly large")
    try:
        token = raw.decode("ascii").strip()
    except UnicodeDecodeError:
        raise ProvisionError("API token must contain ASCII characters only") from None
    if not token or not re.fullmatch(r"[A-Za-z0-9._-]+", token):
        raise ProvisionError("API token file is empty or malformed")
    return token


def load_state(path: Path) -> OwnedState | None:
    if not path.exists():
        return None
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise ProvisionError("Cloudflare ownership state must be a regular file")
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ProvisionError("Cloudflare ownership state must be owner-only")
        payload = json.loads(path.read_text(encoding="utf-8"))
        state = OwnedState(**payload)
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        if isinstance(exc, ProvisionError):
            raise
        raise ProvisionError(
            "Cloudflare ownership state is unreadable or invalid"
        ) from None
    if state.schema_version != STATE_VERSION or state.managed_by != "labgoblin":
        raise ProvisionError("Cloudflare ownership state has an unsupported format")
    return state


def write_state(path: Path, state: OwnedState) -> None:
    if path.parent.exists():
        parent_info = path.parent.lstat()
        if (
            not stat.S_ISDIR(parent_info.st_mode)
            or stat.S_ISLNK(parent_info.st_mode)
            or parent_info.st_uid != os.geteuid()
            or stat.S_IMODE(parent_info.st_mode) & 0o022
        ):
            raise ProvisionError(
                "Cloudflare state directory must be an owned, non-writable directory"
            )
    else:
        path.parent.mkdir(mode=0o700, parents=True)
    if path.exists() or path.is_symlink():
        existing = path.lstat()
        if not stat.S_ISREG(existing.st_mode) or stat.S_ISLNK(existing.st_mode):
            raise ProvisionError("Cloudflare ownership state must be a regular file")
    fd, temporary = tempfile.mkstemp(prefix=".cloudflare-state-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(asdict(state), handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _one(items: list[dict[str, Any]], description: str) -> dict[str, Any] | None:
    if len(items) > 1:
        raise ProvisionError(
            f"Multiple {description} resources matched; refusing to guess"
        )
    return items[0] if items else None


def _result_list(result: Any, description: str) -> list[dict[str, Any]]:
    if not isinstance(result, list) or not all(
        isinstance(item, dict) for item in result
    ):
        raise ApiError(f"Cloudflare returned an invalid {description} list")
    return result


def _ingress() -> list[dict[str, str]]:
    return [
        {"hostname": "__HOSTNAME__", "service": "http://web:8080"},
        {"service": "http_status:404"},
    ]


def _desired_ingress(hostname: str) -> list[dict[str, str]]:
    result = _ingress()
    result[0]["hostname"] = hostname
    return result


def _policy_body(desired: Desired) -> dict[str, Any]:
    if desired.access_selector_kind == "group":
        include = [{"group": {"id": desired.access_selector_value}}]
    else:
        include = [{"email_domain": {"domain": desired.access_selector_value}}]
    return {
        "name": desired.access_policy_name,
        "decision": "allow",
        "include": include,
    }


def _app_body(desired: Desired, policy_id: str) -> dict[str, Any]:
    return {
        "name": desired.access_app_name,
        "domain": desired.hostname,
        "destinations": [{"type": "public", "uri": desired.hostname}],
        "type": "self_hosted",
        "session_duration": desired.session_duration,
        "app_launcher_visible": True,
        "allow_authenticate_via_warp": False,
        "http_only_cookie_attribute": True,
        "same_site_cookie_attribute": "lax",
        "policies": [
            {"id": policy_id, "account_id": desired.account_id, "precedence": 1}
        ],
    }


class Provisioner:
    def __init__(
        self,
        api: CloudflareAPI,
        desired: Desired,
        *,
        state_path: Path,
        app_dir: Path,
        adopt_existing: bool = False,
    ):
        self.api = api
        self.desired = desired
        self.state_path = state_path
        self.app_dir = app_dir
        self.adopt_existing = adopt_existing

    def discover(self) -> Discovery:
        d = self.desired
        state = load_state(self.state_path)
        if state and (
            state.account_id != d.account_id
            or state.zone_name != d.zone_name
            or state.hostname != d.hostname
        ):
            raise ProvisionError(
                "Ownership state belongs to a different Cloudflare deployment"
            )

        zones = _result_list(
            self.api.request(
                "GET",
                "/zones",
                query={"name": d.zone_name, "status": "active", "per_page": "1000"},
            ),
            "zone",
        )
        zones = [z for z in zones if str(z.get("name", "")).lower() == d.zone_name]
        zone = _one(zones, "active zone")
        if not zone or not zone.get("id"):
            raise ProvisionError(f"Active Cloudflare zone {d.zone_name} was not found")
        zone_id = _validate_resource_identifier(zone["id"], "zone")

        tunnels = _result_list(
            self.api.request(
                "GET",
                f"/accounts/{d.account_id}/cfd_tunnel",
                query={
                    "is_deleted": "false",
                    "name": d.tunnel_name,
                    "per_page": "1000",
                },
            ),
            "Tunnel",
        )
        tunnel = _one([t for t in tunnels if t.get("name") == d.tunnel_name], "Tunnel")
        tunnel_config = None
        if tunnel:
            tunnel_id = _validate_resource_identifier(tunnel.get("id"), "Tunnel")
            tunnel_config = self.api.request(
                "GET", f"/accounts/{d.account_id}/cfd_tunnel/{tunnel_id}/configurations"
            )

        policies = _result_list(
            self.api.request(
                "GET",
                f"/accounts/{d.account_id}/access/policies",
                query={"per_page": "1000"},
            ),
            "Access policy",
        )
        policy = _one(
            [p for p in policies if p.get("name") == d.access_policy_name],
            "Access policy",
        )
        apps = _result_list(
            self.api.request(
                "GET",
                f"/accounts/{d.account_id}/access/apps",
                query={"per_page": "1000"},
            ),
            "Access application",
        )
        app = _one(
            [a for a in apps if str(a.get("domain", "")).lower() == d.hostname],
            "Access application",
        )
        if app:
            app_id = _validate_resource_identifier(app.get("id"), "Access application")
            app = self.api.request(
                "GET", f"/accounts/{d.account_id}/access/apps/{app_id}"
            )
            if not isinstance(app, dict):
                raise ApiError("Cloudflare returned an invalid Access application")
        records = _result_list(
            self.api.request(
                "GET",
                f"/zones/{zone_id}/dns_records",
                query={
                    "name.exact": d.hostname,
                    "type": "CNAME",
                    "per_page": "1000",
                },
            ),
            "DNS record",
        )
        dns = _one(
            [r for r in records if str(r.get("name", "")).lower() == d.hostname],
            "DNS record",
        )
        discovery = Discovery(zone_id, tunnel, tunnel_config, policy, app, dns, state)
        self._verify_ownership(discovery)
        return discovery

    def _verify_ownership(self, found: Discovery) -> None:
        resources = {
            "Tunnel": (found.tunnel, "tunnel_id"),
            "Access policy": (found.policy, "access_policy_id"),
            "Access application": (found.app, "access_app_id"),
            "DNS record": (found.dns, "dns_record_id"),
        }
        for label, (resource, field) in resources.items():
            if resource is None:
                continue
            resource_id = str(resource.get("id", ""))
            if found.state and getattr(found.state, field) == resource_id:
                continue
            if not self.adopt_existing:
                raise ProvisionError(
                    f"An unmanaged {label} already matches this deployment; "
                    "inspect it and use --adopt-existing only if it is dedicated to LabGoblin"
                )
        if found.tunnel:
            actual = (found.tunnel_config or {}).get("config", {}).get("ingress")
            if actual != _desired_ingress(self.desired.hostname):
                raise ProvisionError(
                    "Existing Tunnel has unexpected ingress rules; refusing to overwrite it"
                )
        if found.policy and not self._policy_matches(found.policy):
            raise ProvisionError(
                "Existing Access policy is broader than the requested policy"
            )
        if found.app:
            expected_policy = {
                "id": str(found.policy["id"]) if found.policy else "",
                "account_id": self.desired.account_id,
                "precedence": 1,
            }
            policies = found.app.get("policies")
            policy_links = []
            if isinstance(policies, list):
                policy_links = [
                    {key: item.get(key) for key in expected_policy}
                    for item in policies
                    if isinstance(item, dict)
                ]
            if (
                found.app.get("name") != self.desired.access_app_name
                or found.app.get("domain") != self.desired.hostname
                or found.app.get("type") != "self_hosted"
                or found.app.get("destinations")
                != [{"type": "public", "uri": self.desired.hostname}]
                or found.app.get("session_duration") != self.desired.session_duration
                or found.app.get("allow_authenticate_via_warp") is not False
                or found.app.get("http_only_cookie_attribute") is not True
                or found.app.get("same_site_cookie_attribute") != "lax"
                or policy_links != [expected_policy]
            ):
                raise ProvisionError(
                    "Existing Access application does not exactly match the "
                    "dedicated LabGoblin boundary"
                )
        if found.dns:
            expected = (
                f"{found.tunnel['id']}.cfargotunnel.com" if found.tunnel else None
            )
            if (
                found.dns.get("type") != "CNAME"
                or found.dns.get("content") != expected
                or found.dns.get("proxied") is not True
            ):
                raise ProvisionError(
                    "Existing DNS record conflicts with the requested Tunnel"
                )

    def _policy_matches(self, policy: dict[str, Any]) -> bool:
        return (
            policy.get("decision") == "allow"
            and policy.get("include") == _policy_body(self.desired)["include"]
            and not policy.get("exclude")
            and not policy.get("require")
        )

    def changes(self, found: Discovery) -> list[Change]:
        changes: list[Change] = []
        for exists, resource, detail in (
            (
                found.policy,
                "Access policy",
                f"allow {self.desired.access_selector_kind} "
                f"{self.desired.access_selector_value}",
            ),
            (found.app, "Access application", self.desired.hostname),
            (found.tunnel, "Tunnel", self.desired.tunnel_name),
            (found.dns, "proxied CNAME", self.desired.hostname),
        ):
            changes.append(Change("keep" if exists else "create", resource, detail))
        if found.tunnel:
            changes.append(
                Change("keep", "Tunnel ingress", "http://web:8080 + 404 catch-all")
            )
        changes.append(
            Change(
                "keep" if self._local_matches(found) else "configure",
                "local host",
                self.desired.hostname,
            )
        )
        return changes

    def _local_matches(self, found: Discovery) -> bool:
        if not found.app or not found.tunnel:
            return False
        audience = str(found.app.get("aud", ""))
        if not audience or not ID_RE.fullmatch(audience):
            return False
        env_path = self.app_dir / ".env"
        token_path = Path(
            os.environ.get("LABGOBLIN_CLOUDFLARE_TOKEN_FILE", DEFAULT_TOKEN_DEST)
        )
        if not env_path.is_file() or not token_path.is_file():
            return False
        expected = {
            "CLOUDFLARE_TUNNEL_ENABLED": "true",
            "CLOUDFLARE_PUBLIC_HOSTNAME": self.desired.hostname,
            "CLOUDFLARE_ACCESS_REQUIRED": "true",
            "CLOUDFLARE_ACCESS_TEAM_DOMAIN": self.desired.team_domain,
            "CLOUDFLARE_ACCESS_AUDIENCE": audience,
            "HTTP_BIND_ADDRESS": "127.0.0.1",
        }
        actual: dict[str, str] = {}
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                actual[key] = value
        return all(actual.get(key) == value for key, value in expected.items())

    def apply(self, found: Discovery) -> OwnedState:
        d = self.desired
        created: list[tuple[str, str, str]] = []
        local_enabled = False
        try:
            policy = found.policy
            if policy is None:
                policy = self.api.request(
                    "POST",
                    f"/accounts/{d.account_id}/access/policies",
                    body=_policy_body(d),
                )
                self._require_resource(policy, "Access policy")
                created.append(
                    (
                        "Access policy",
                        f"/accounts/{d.account_id}/access/policies/{policy['id']}",
                        "",
                    )
                )

            app = found.app
            if app is None:
                app = self.api.request(
                    "POST",
                    f"/accounts/{d.account_id}/access/apps",
                    body=_app_body(d, str(policy["id"])),
                )
                self._require_resource(app, "Access application")
                created.append(
                    (
                        "Access application",
                        f"/accounts/{d.account_id}/access/apps/{app['id']}",
                        "",
                    )
                )
            audience = str(app.get("aud", ""))
            _validate_identifier(audience, "Cloudflare Access audience")

            tunnel = found.tunnel
            if tunnel is None:
                tunnel = self.api.request(
                    "POST",
                    f"/accounts/{d.account_id}/cfd_tunnel",
                    body={"name": d.tunnel_name, "config_src": "cloudflare"},
                )
                self._require_resource(tunnel, "Tunnel")
                created.append(
                    (
                        "Tunnel",
                        f"/accounts/{d.account_id}/cfd_tunnel/{tunnel['id']}",
                        "",
                    )
                )
                self.api.request(
                    "PUT",
                    f"/accounts/{d.account_id}/cfd_tunnel/{tunnel['id']}/configurations",
                    body={"config": {"ingress": _desired_ingress(d.hostname)}},
                )

            if not self._local_matches(
                Discovery(
                    found.zone_id,
                    tunnel,
                    found.tunnel_config,
                    policy,
                    app,
                    found.dns,
                    found.state,
                )
            ):
                token = self.api.request(
                    "GET", f"/accounts/{d.account_id}/cfd_tunnel/{tunnel['id']}/token"
                )
                if not isinstance(token, str) or not token or len(token) > 8192:
                    raise ApiError("Cloudflare returned an invalid Tunnel token")
                self._configure_local(token, audience)
                local_enabled = True

            dns = found.dns
            if dns is None:
                dns = self.api.request(
                    "POST",
                    f"/zones/{found.zone_id}/dns_records",
                    body={
                        "type": "CNAME",
                        "name": d.hostname,
                        "content": f"{tunnel['id']}.cfargotunnel.com",
                        "proxied": True,
                        "ttl": 1,
                        "comment": "Managed by LabGoblin Cloudflare provisioning",
                    },
                )
                self._require_resource(dns, "DNS record")
                created.append(
                    (
                        "DNS record",
                        f"/zones/{found.zone_id}/dns_records/{dns['id']}",
                        "",
                    )
                )

            state = OwnedState(
                schema_version=STATE_VERSION,
                managed_by="labgoblin",
                account_id=d.account_id,
                zone_id=found.zone_id,
                zone_name=d.zone_name,
                hostname=d.hostname,
                access_selector_kind=d.access_selector_kind,
                access_selector_value=d.access_selector_value,
                team_domain=d.team_domain,
                tunnel_id=str(tunnel["id"]),
                tunnel_name=d.tunnel_name,
                access_app_id=str(app["id"]),
                access_app_name=d.access_app_name,
                access_audience=audience,
                access_policy_id=str(policy["id"]),
                access_policy_name=d.access_policy_name,
                dns_record_id=str(dns["id"]),
                updated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
            )
            write_state(self.state_path, state)
            return state
        except AmbiguousPostError:
            # A POST may have succeeded remotely. Deleting prior resources could
            # invalidate that unknown resource, so leave the unpublished partial
            # set for the next discovery/explicit adoption pass.
            raise
        except Exception:
            if local_enabled:
                self._disable_local_best_effort()
            for _name, path, _unused in reversed(created):
                try:
                    self.api.request("DELETE", path)
                except ProvisionError:
                    pass
            raise

    @staticmethod
    def _require_resource(value: Any, label: str) -> None:
        if not isinstance(value, dict) or not value.get("id"):
            raise ApiError(f"Cloudflare returned an invalid {label} resource")
        _validate_resource_identifier(value["id"], label)

    def _configure_local(self, tunnel_token: str, audience: str) -> None:
        helper = self.app_dir / "deploy" / "configure-cloudflare.sh"
        if not helper.is_file():
            raise ProvisionError(f"Missing local Cloudflare helper: {helper}")
        run_dir = Path("/run/labgoblin")
        try:
            run_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            run_info = run_dir.lstat()
        except OSError as exc:
            raise ProvisionError(
                f"Unable to prepare protected runtime directory: {exc.strerror}"
            ) from None
        if (
            not stat.S_ISDIR(run_info.st_mode)
            or stat.S_ISLNK(run_info.st_mode)
            or run_info.st_uid != os.geteuid()
        ):
            raise ProvisionError("Protected runtime path must be an owned directory")
        os.chmod(run_dir, 0o700)
        fd, name = tempfile.mkstemp(prefix="cloudflare-tunnel-token-", dir=run_dir)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="ascii") as handle:
                handle.write(tunnel_token)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            command = [
                "sh",
                str(helper),
                "enable",
                "--hostname",
                self.desired.hostname,
                "--team-domain",
                self.desired.team_domain,
                "--audience",
                audience,
                "--token-file",
                name,
                "--app-dir",
                str(self.app_dir),
            ]
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as exc:
            raise ProvisionError(
                f"Local Cloudflare activation failed with exit code {exc.returncode}"
            ) from None
        finally:
            try:
                os.unlink(name)
            except FileNotFoundError:
                pass

    def _disable_local_best_effort(self) -> None:
        helper = self.app_dir / "deploy" / "configure-cloudflare.sh"
        try:
            subprocess.run(
                ["sh", str(helper), "disable", "--app-dir", str(self.app_dir)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("mode", choices=("plan", "apply"))
    result.add_argument("--account-id", required=True)
    result.add_argument("--zone", required=True)
    result.add_argument("--hostname", required=True)
    selector = result.add_mutually_exclusive_group(required=True)
    selector.add_argument(
        "--access-group-id",
        help="preferred: UUID of a pre-created least-privilege Access group",
    )
    selector.add_argument(
        "--allow-email-domain",
        help="fallback: allow identities from this exact email domain",
    )
    result.add_argument("--team-domain", required=True)
    result.add_argument("--api-token-file", type=Path, required=True)
    result.add_argument("--tunnel-name")
    result.add_argument("--session-duration", default="12h")
    result.add_argument("--app-dir", type=Path, default=Path("/opt/labgoblin/app"))
    result.add_argument("--state-file", type=Path, default=DEFAULT_STATE)
    result.add_argument("--adopt-existing", action="store_true")
    result.add_argument(
        "--yes", action="store_true", help="confirm apply without a prompt"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if os.geteuid() != 0:
            raise ProvisionError("Run this host provisioning command as root")
        os.umask(0o077)
        desired = desired_from_args(args)
        token = read_protected_secret(args.api_token_file)
        provisioner = Provisioner(
            CloudflareAPI(token),
            desired,
            state_path=args.state_file,
            app_dir=args.app_dir,
            adopt_existing=args.adopt_existing,
        )
        found = provisioner.discover()
        changes = provisioner.changes(found)
        print("Cloudflare provisioning plan:")
        print(f"  account:  {desired.account_id}")
        print(f"  zone:     {desired.zone_name}")
        print(f"  hostname: {desired.hostname}")
        for change in changes:
            print(f"  {change.action.upper():9} {change.resource}: {change.detail}")
        if args.mode == "plan":
            return 0
        if not args.yes:
            if not sys.stdin.isatty():
                raise ProvisionError(
                    "Apply requires --yes when input is not interactive"
                )
            answer = input("Apply this plan? [y/N] ").strip().lower()
            if answer not in {"y", "yes"}:
                print("No changes made.")
                return 0
        state = provisioner.apply(found)
        print(f"Cloudflare publication is configured for https://{state.hostname}.")
        print(f"Nonsecret ownership metadata: {args.state_file}")
        return 0
    except ProvisionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
