import argparse
import importlib.util
from pathlib import Path
import stat
import sys
import urllib.error

import pytest

ROOT = Path(__file__).parents[2]
SPEC = importlib.util.spec_from_file_location(
    "labgoblin_cloudflare_provision", ROOT / "deploy" / "provision_cloudflare.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

from labgoblin_cloudflare_provision import (  # noqa: E402
    AmbiguousPostError,
    ApiError,
    CloudflareAPI,
    Desired,
    Discovery,
    OwnedState,
    ProvisionError,
    Provisioner,
    _app_body,
    _policy_body,
    desired_from_args,
    read_protected_secret,
    write_state,
)


class FakeAPI:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, path, *, query=None, body=None):
        self.calls.append((method, path, query, body))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FailingOpener:
    def __init__(self):
        self.calls = 0

    def open(self, request, timeout):
        self.calls += 1
        raise urllib.error.URLError("connection failed")


def desired() -> Desired:
    return Desired(
        account_id="account_12345678",
        zone_name="example.edu",
        hostname="lab.example.edu",
        access_selector_kind="email_domain",
        access_selector_value="students.example.edu",
        team_domain="school.cloudflareaccess.com",
        tunnel_name="labgoblin-lab-example-edu",
        access_app_name="LabGoblin — lab.example.edu",
        access_policy_name="LabGoblin — allow students.example.edu",
        session_duration="12h",
    )


def empty_discovery() -> Discovery:
    return Discovery("zone-id", None, None, None, None, None, None)


def test_secret_file_must_be_owner_only(tmp_path):
    token = tmp_path / "token"
    token.write_text("secret-token\n")
    token.chmod(0o640)
    with pytest.raises(ProvisionError, match="group or others"):
        read_protected_secret(token)
    token.chmod(0o600)
    assert read_protected_secret(token) == "secret-token"


def test_get_retries_but_ambiguous_post_does_not(monkeypatch):
    api = CloudflareAPI("api-secret-token")
    opener = FailingOpener()
    api._opener = opener
    monkeypatch.setattr(api, "_wait_before_retry", lambda attempt, retry_after: None)
    with pytest.raises(ApiError) as get_error:
        api.request("GET", "/zones")
    assert opener.calls == 3
    assert "api-secret-token" not in str(get_error.value)

    opener.calls = 0
    with pytest.raises(AmbiguousPostError, match="adopt-existing"):
        api.request("POST", "/accounts/account/tunnel", body={"name": "example"})
    assert opener.calls == 1


def test_argument_validation_rejects_apex_and_foreign_team_domain():
    values = argparse.Namespace(
        account_id="account_12345678",
        zone="example.edu",
        hostname="example.edu",
        allow_email_domain="students.example.edu",
        access_group_id=None,
        team_domain="attacker.example.com",
        tunnel_name=None,
        session_duration="12h",
    )
    with pytest.raises(ProvisionError):
        desired_from_args(values)


def test_access_group_is_preferred_policy_selector():
    group_id = "f174e90a-fafe-4643-bbbc-4a0ed4fc8415"
    values = argparse.Namespace(
        account_id="account_12345678",
        zone="example.edu",
        hostname="lab.example.edu",
        allow_email_domain=None,
        access_group_id=group_id,
        team_domain="school.cloudflareaccess.com",
        tunnel_name=None,
        session_duration="12h",
    )
    configured = desired_from_args(values)
    assert configured.access_selector_kind == "group"
    assert configured.access_selector_value == group_id
    policy = _policy_body(configured)
    assert policy["decision"] == "allow"
    assert policy["include"] == [{"group": {"id": group_id}}]
    assert "everyone" not in str(policy).lower()

    application = _app_body(configured, "policy-id")
    assert application["destinations"] == [{"type": "public", "uri": "lab.example.edu"}]
    assert application["policies"] == [
        {
            "id": "policy-id",
            "account_id": "account_12345678",
            "precedence": 1,
        }
    ]
    assert application["allow_authenticate_via_warp"] is False
    assert application["http_only_cookie_attribute"] is True
    assert application["same_site_cookie_attribute"] == "lax"


def test_argument_validation_rejects_unsafe_tunnel_name():
    values = argparse.Namespace(
        account_id="account_12345678",
        zone="example.edu",
        hostname="lab.example.edu",
        allow_email_domain="students.example.edu",
        access_group_id=None,
        team_domain="school.cloudflareaccess.com",
        tunnel_name="unsafe\nname",
        session_duration="12h",
    )
    with pytest.raises(ProvisionError, match="tunnel-name"):
        desired_from_args(values)


def test_discovery_aborts_on_unmanaged_name_collision(tmp_path):
    api = FakeAPI(
        [
            [{"id": "zone-id", "name": "example.edu"}],
            [{"id": "tunnel-id", "name": desired().tunnel_name}],
            {
                "config": {
                    "ingress": [
                        {"hostname": desired().hostname, "service": "http://web:8080"},
                        {"service": "http_status:404"},
                    ]
                }
            },
            [],
            [],
            [],
        ]
    )
    provisioner = Provisioner(
        api, desired(), state_path=tmp_path / "state.json", app_dir=tmp_path
    )
    with pytest.raises(ProvisionError, match="unmanaged Tunnel"):
        provisioner.discover()


def test_plan_is_read_only(tmp_path):
    api = FakeAPI([])
    provisioner = Provisioner(
        api, desired(), state_path=tmp_path / "state.json", app_dir=tmp_path
    )
    changes = provisioner.changes(empty_discovery())
    assert [change.action for change in changes] == [
        "create",
        "create",
        "create",
        "create",
        "configure",
    ]
    assert api.calls == []
    assert not (tmp_path / "state.json").exists()


def test_existing_access_app_must_have_exact_single_policy(tmp_path):
    policy = {
        "id": "policy-id",
        "name": desired().access_policy_name,
        "decision": "allow",
        "include": [{"email_domain": {"domain": desired().access_selector_value}}],
    }
    app = {
        "id": "app-id",
        "name": desired().access_app_name,
        "domain": desired().hostname,
        "type": "self_hosted",
        "destinations": [{"type": "public", "uri": desired().hostname}],
        "policies": [
            {
                "id": "different-policy",
                "account_id": desired().account_id,
                "precedence": 1,
            }
        ],
    }
    provisioner = Provisioner(
        FakeAPI([]),
        desired(),
        state_path=tmp_path / "state.json",
        app_dir=tmp_path,
        adopt_existing=True,
    )
    found = Discovery("zone-id", None, None, policy, app, None, None)
    with pytest.raises(ProvisionError, match="does not exactly match"):
        provisioner._verify_ownership(found)


def test_apply_creates_access_before_tunnel_and_publishes_dns_last(
    tmp_path, monkeypatch
):
    api = FakeAPI(
        [
            {"id": "policy-id"},
            {"id": "app-id", "aud": "audience_12345678"},
            {"id": "tunnel-id"},
            {"version": 1},
            "tunnel-token-that-must-not-be-logged",
            {"id": "dns-id"},
        ]
    )
    provisioner = Provisioner(
        api, desired(), state_path=tmp_path / "state.json", app_dir=tmp_path
    )
    configured = []
    monkeypatch.setattr(
        provisioner,
        "_configure_local",
        lambda token, aud: configured.append((token, aud)),
    )
    monkeypatch.setattr(provisioner, "_local_matches", lambda found: False)

    state = provisioner.apply(empty_discovery())

    assert [call[0:2] for call in api.calls] == [
        ("POST", f"/accounts/{desired().account_id}/access/policies"),
        ("POST", f"/accounts/{desired().account_id}/access/apps"),
        ("POST", f"/accounts/{desired().account_id}/cfd_tunnel"),
        (
            "PUT",
            f"/accounts/{desired().account_id}/cfd_tunnel/tunnel-id/configurations",
        ),
        ("GET", f"/accounts/{desired().account_id}/cfd_tunnel/tunnel-id/token"),
        ("POST", "/zones/zone-id/dns_records"),
    ]
    assert configured == [("tunnel-token-that-must-not-be-logged", "audience_12345678")]
    assert state.dns_record_id == "dns-id"
    assert "token" not in (tmp_path / "state.json").read_text().lower()
    assert stat.S_IMODE((tmp_path / "state.json").stat().st_mode) == 0o600


def test_apply_rollback_deletes_only_new_resources(tmp_path, monkeypatch):
    api = FakeAPI(
        [
            {"id": "policy-id"},
            {"id": "app-id", "aud": "audience_12345678"},
            {"id": "tunnel-id"},
            {"version": 1},
            "tunnel-token-that-must-not-be-logged",
            ProvisionError("local failed"),
            {},
            {},
            {},
        ]
    )
    provisioner = Provisioner(
        api, desired(), state_path=tmp_path / "state.json", app_dir=tmp_path
    )
    monkeypatch.setattr(provisioner, "_configure_local", lambda token, aud: None)
    monkeypatch.setattr(provisioner, "_local_matches", lambda found: False)
    monkeypatch.setattr(provisioner, "_disable_local_best_effort", lambda: None)

    with pytest.raises(ProvisionError, match="local failed"):
        provisioner.apply(empty_discovery())

    deletes = [call[1] for call in api.calls if call[0] == "DELETE"]
    assert deletes == [
        f"/accounts/{desired().account_id}/cfd_tunnel/tunnel-id",
        f"/accounts/{desired().account_id}/access/apps/app-id",
        f"/accounts/{desired().account_id}/access/policies/policy-id",
    ]


def test_write_state_contains_no_secrets(tmp_path):
    state = OwnedState(
        1,
        "labgoblin",
        "account",
        "zone",
        "example.edu",
        "lab.example.edu",
        "email_domain",
        "students.example.edu",
        "school.cloudflareaccess.com",
        "tunnel",
        "tunnel-name",
        "app",
        "app-name",
        "audience",
        "policy",
        "policy-name",
        "dns",
        "2026-09-12T00:00:00+00:00",
    )
    path = tmp_path / "state.json"
    write_state(path, state)
    data = path.read_text()
    assert "api_token" not in data
    assert "tunnel_token" not in data


def test_write_state_does_not_change_existing_parent_permissions(tmp_path):
    parent = tmp_path / "state-directory"
    parent.mkdir(mode=0o755)
    before = stat.S_IMODE(parent.stat().st_mode)
    state = OwnedState(
        1,
        "labgoblin",
        "account",
        "zone",
        "example.edu",
        "lab.example.edu",
        "email_domain",
        "students.example.edu",
        "school.cloudflareaccess.com",
        "tunnel",
        "tunnel-name",
        "app",
        "app-name",
        "audience",
        "policy",
        "policy-name",
        "dns",
        "2026-09-12T00:00:00+00:00",
    )
    write_state(parent / "state.json", state)
    assert stat.S_IMODE(parent.stat().st_mode) == before
