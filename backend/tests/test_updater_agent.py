import importlib.util
import fcntl
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[2] / "deploy" / "updater_agent.py"
SPEC = importlib.util.spec_from_file_location("updater_agent", MODULE_PATH)
updater = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(updater)


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8080/api/ready",
        "http://example.com/api/ready",
        "http://localhost:8080/api/ready",
        "http://user:pass@127.0.0.1/api/ready",
        "http://127.0.0.1/api/ready?next=http://example.com",
    ],
)
def test_health_url_rejects_non_literal_or_unsafe_targets(monkeypatch, url):
    monkeypatch.setattr(updater, "HEALTH_URL", url)
    with pytest.raises(RuntimeError, match="loopback"):
        updater.validate_health_url()


@pytest.mark.parametrize(
    "url", ["http://127.0.0.1:8080/api/ready", "http://[::1]:8080/api/ready"]
)
def test_health_url_accepts_loopback_http(monkeypatch, url):
    monkeypatch.setattr(updater, "HEALTH_URL", url)
    updater.validate_health_url()


def test_restore_rejects_backup_outside_state_directory(monkeypatch, tmp_path):
    state = tmp_path / "state"
    outside = tmp_path / "state-escape.dump"
    outside.write_bytes(b"not a database")
    monkeypatch.setattr(updater, "STATE_DIR", state)

    with pytest.raises(RuntimeError, match="outside"):
        updater.restore_database(outside)


def test_run_applies_command_timeout(monkeypatch, tmp_path):
    captured = {}

    def fake_run(args, **kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(updater.subprocess, "run", fake_run)
    monkeypatch.setattr(updater, "COMMAND_TIMEOUT", 123)
    updater.run(["true"], cwd=tmp_path)

    assert captured["timeout"] == 123


def test_check_uses_operation_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(updater, "STATE_DIR", tmp_path)
    called = False

    def fake_check(_payload):
        nonlocal called
        called = True

    monkeypatch.setattr(updater, "check_update", fake_check)
    with (tmp_path / "update.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            updater.check_update_locked({})

    assert called is False


def test_check_rejects_queued_operation_without_losing_state(monkeypatch, tmp_path):
    monkeypatch.setattr(updater, "STATE_DIR", tmp_path)
    expected = {"operation": {"id": "op-1", "status": "queued"}, "keep": "value"}
    updater.write_state(expected)

    with pytest.raises(BlockingIOError):
        updater.check_update_locked({})

    assert updater.read_state() == expected
    assert not list(tmp_path.glob(".update-state.*.tmp"))


def test_recovery_quiesces_writers_before_restore_and_checks_health(
    monkeypatch, tmp_path
):
    events = []
    backup = tmp_path / "backup.dump"

    monkeypatch.setattr(
        updater, "compose", lambda *args, **_kwargs: events.append(("compose", args))
    )
    monkeypatch.setattr(
        updater, "run", lambda args, **_kwargs: events.append(("run", tuple(args)))
    )
    monkeypatch.setattr(
        updater,
        "restore_database",
        lambda path: events.append(("restore", path)),
    )
    monkeypatch.setattr(
        updater, "wait_for_health", lambda: events.append(("health", None))
    )
    monkeypatch.setattr(
        updater, "install_agent_from", lambda path: events.append(("agent", path))
    )

    updater.recover_version("a" * 40, backup)

    assert events[0] == ("compose", ("stop", "api", "web"))
    assert events.index(("restore", backup)) < events.index(
        ("compose", ("up", "-d", "--build", "--remove-orphans"))
    )
    assert events.index(
        ("compose", ("up", "-d", "--build", "--remove-orphans"))
    ) < events.index(("health", None))


def test_recovery_restore_failure_keeps_application_stopped(monkeypatch, tmp_path):
    compose_calls = []

    monkeypatch.setattr(
        updater,
        "compose",
        lambda *args, **_kwargs: compose_calls.append(args),
    )
    monkeypatch.setattr(updater, "run", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        updater,
        "restore_database",
        lambda _path: (_ for _ in ()).throw(RuntimeError("restore fault")),
    )

    with pytest.raises(RuntimeError, match="restore fault"):
        updater.recover_version("b" * 40, tmp_path / "backup.dump")

    assert compose_calls == [("stop", "api", "web")]


def test_failed_recovery_is_reported_and_preserves_original_cause(monkeypatch):
    original = RuntimeError("target health fault")
    monkeypatch.setattr(
        updater,
        "recover_version",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("restore fault")),
    )

    with pytest.raises(RuntimeError, match="API remains stopped") as exc:
        updater.recover_after_failure("Update", original, "a" * 40, None)

    assert exc.value.__cause__ is original
    assert "restore fault" in str(exc.value)


def test_compose_allows_bootstrap_token_to_be_removed_after_enrollment():
    compose_source = MODULE_PATH.parents[1].joinpath("docker-compose.yml").read_text()
    assert "BOOTSTRAP_ADMIN_TOKEN: ${BOOTSTRAP_ADMIN_TOKEN:-}" in compose_source


def test_compose_keeps_cloudflare_profile_enabled_across_updates(monkeypatch, tmp_path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    app_dir.joinpath(".env").write_text("CLOUDFLARE_TUNNEL_ENABLED=true\n")
    app_dir.joinpath("docker-compose.yml").write_text(
        "services:\n  cloudflared:\n    profiles: [cloudflare]\n"
    )
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["cwd"] = kwargs["cwd"]
        return object()

    monkeypatch.setattr(updater, "APP_DIR", app_dir)
    monkeypatch.setattr(updater, "run", fake_run)
    updater.compose("up", "-d")

    assert captured["args"][:8] == [
        "docker",
        "compose",
        "--env-file",
        str(app_dir / ".env"),
        "--project-directory",
        str(app_dir),
        "--profile",
        "cloudflare",
    ]
    assert captured["args"][8:] == ["up", "-d"]


def test_compose_omits_cloudflare_profile_for_preintegration_rollback(
    monkeypatch, tmp_path
):
    app_dir = tmp_path / "app"
    old_worktree = tmp_path / "old"
    app_dir.mkdir()
    old_worktree.mkdir()
    app_dir.joinpath(".env").write_text("CLOUDFLARE_TUNNEL_ENABLED=true\n")
    old_worktree.joinpath("docker-compose.yml").write_text("services:\n  web: {}\n")
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        return object()

    monkeypatch.setattr(updater, "APP_DIR", app_dir)
    monkeypatch.setattr(updater, "run", fake_run)
    updater.compose("build", project_dir=old_worktree)

    assert "--profile" not in captured["args"]
