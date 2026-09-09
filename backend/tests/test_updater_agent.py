import importlib.util
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
