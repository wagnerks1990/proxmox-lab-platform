import json
import os
from pathlib import Path
import stat
import subprocess


ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "deploy" / "configure-cloudflare.sh"
COMPOSE = ROOT / "docker-compose.yml"


def _fake_commands(tmp_path: Path) -> tuple[Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    docker_log = tmp_path / "docker.log"
    fake_id = bin_dir / "id"
    fake_id.write_text(
        '#!/bin/sh\nif [ "${1:-}" = "-u" ]; then echo 0; else /usr/bin/id "$@"; fi\n'
    )
    fake_docker = bin_dir / "docker"
    fake_docker.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$FAKE_DOCKER_LOG"\n'
        'case " $* " in\n'
        '  *" ps --status running --services cloudflared "*) '
        '[ "${FAKE_CLOUDFLARED_RUNNING:-false}" = true ] && echo cloudflared ;;\n'
        '  *" up "*) [ "${FAKE_DOCKER_UP_FAIL:-false}" = true ] && exit 1 ;;\n'
        "esac\nexit 0\n"
    )
    fake_curl = bin_dir / "curl"
    fake_curl.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$FAKE_CURL_LOG"\n'
        '[ "${FAKE_CURL_FAIL:-false}" != true ]\n'
    )
    fake_getent = bin_dir / "getent"
    fake_getent.write_text(
        '#!/bin/sh\n[ "${1:-}" = group ] && [ "${2:-}" = labgoblin-cloudflared ] && '
        "printf 'labgoblin-cloudflared:x:4242:\\n'\n"
    )
    fake_groupadd = bin_dir / "groupadd"
    fake_groupadd.write_text("#!/bin/sh\nexit 0\n")
    fake_install = bin_dir / "install"
    fake_install.write_text(
        "#!/bin/sh\n"
        "directory=false\nmode=\n"
        'while [ "$#" -gt 0 ]; do\n'
        '  case "$1" in\n'
        "    -d) directory=true; shift ;;\n"
        "    -o|-g) shift 2 ;;\n"
        "    -m) mode=$2; shift 2 ;;\n"
        "    *) break ;;\n"
        "  esac\n"
        "done\n"
        'if [ "$directory" = true ]; then mkdir -p "$1"; chmod "$mode" "$1"; '
        'else cp "$1" "$2"; chmod "$mode" "$2"; fi\n'
    )
    fake_id.chmod(0o755)
    fake_docker.chmod(0o755)
    fake_getent.chmod(0o755)
    fake_groupadd.chmod(0o755)
    fake_install.chmod(0o755)
    fake_curl.chmod(0o755)
    return bin_dir, docker_log


def _run_config(
    tmp_path: Path, *args: str, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    app_dir = tmp_path / "app"
    if not app_dir.exists():
        app_dir.mkdir()
        app_dir.joinpath(".env").write_text(
            "AUTH_COOKIE_SECURE=false\n"
            "BROWSER_TRUSTED_ORIGINS=https://existing.example.edu\n"
            "UNCHANGED=keep-me\n"
        )
        app_dir.joinpath("docker-compose.yml").write_text(COMPOSE.read_text())
    bin_dir, docker_log = _fake_commands(tmp_path)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "FAKE_DOCKER_LOG": str(docker_log),
        "FAKE_CURL_LOG": str(tmp_path / "curl.log"),
        "LABGOBLIN_APP_DIR": str(app_dir),
        "LABGOBLIN_CLOUDFLARE_TOKEN_FILE": str(tmp_path / "installed-token"),
    }
    env.update(extra_env or {})
    return subprocess.run(
        ["sh", str(SCRIPT), *args],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_cloudflare_compose_service_is_profiled_and_isolated():
    source = COMPOSE.read_text()
    cloudflared = source.split("  cloudflared:", 1)[1].split("\nvolumes:", 1)[0]
    assert 'profiles: ["cloudflare"]' in cloudflared
    assert "cloudflare/cloudflared:2026.9.1" in cloudflared
    assert "--token-file" in cloudflared
    assert "${CLOUDFLARE_TUNNEL_TOKEN:" not in cloudflared
    assert "read_only: true" in cloudflared
    assert "no-new-privileges:true" in cloudflared
    assert "cap_drop:" in cloudflared and "- ALL" in cloudflared
    assert "${CLOUDFLARE_TUNNEL_GID:-65534}" in cloudflared
    assert "- cloudflare-edge" in cloudflared
    assert "${HTTP_BIND_ADDRESS:-0.0.0.0}:${HTTP_PORT:-8080}:8080" in source
    assert '["CMD", "cloudflared", "tunnel", "ready"]' in cloudflared


def test_enable_is_idempotent_and_disable_fails_closed(tmp_path):
    token_file = tmp_path / "source-token"
    secret = "eyJh.test-cloudflare-token.signature"
    token_file.write_text(secret + "\n")
    enable_args = (
        "enable",
        "--hostname",
        "lab.example.edu",
        "--team-domain",
        "school.cloudflareaccess.com",
        "--audience",
        "access-audience-1234",
        "--token-file",
        str(token_file),
    )

    first = _run_config(tmp_path, *enable_args)
    assert first.returncode == 0, first.stderr
    second = _run_config(tmp_path, *enable_args)
    assert second.returncode == 0, second.stderr

    env_file = tmp_path / "app" / ".env"
    configured = env_file.read_text()
    assert configured.count("# BEGIN LABGOBLIN CLOUDFLARE") == 1
    assert "HTTP_BIND_ADDRESS=127.0.0.1" in configured
    assert "AUTH_COOKIE_SECURE=true" in configured
    assert "BROWSER_TRUSTED_ORIGINS=https://lab.example.edu" in configured
    assert "CLOUDFLARE_ACCESS_REQUIRED=true" in configured
    assert "CLOUDFLARE_ACCESS_TEAM_DOMAIN=school.cloudflareaccess.com" in configured
    assert "CLOUDFLARE_ACCESS_AUDIENCE=access-audience-1234" in configured
    assert "CLOUDFLARE_TUNNEL_GID=4242" in configured
    assert secret not in configured
    assert (tmp_path / "installed-token").read_text() == secret + "\n"
    assert stat.S_IMODE((tmp_path / "installed-token").stat().st_mode) == 0o440
    assert secret not in (tmp_path / "docker.log").read_text()

    disabled = _run_config(tmp_path, "disable")
    assert disabled.returncode == 0, disabled.stderr
    restored = env_file.read_text()
    assert "BEGIN LABGOBLIN CLOUDFLARE" not in restored
    assert "AUTH_COOKIE_SECURE=false" in restored
    assert "BROWSER_TRUSTED_ORIGINS=https://existing.example.edu" in restored
    assert "UNCHANGED=keep-me" in restored
    assert "HTTP_BIND_ADDRESS=127.0.0.1" in restored
    assert (tmp_path / "installed-token").exists()

    docker_log = (tmp_path / "docker.log").read_text()
    assert "--wait --wait-timeout 120" in docker_log
    assert secret not in docker_log
    assert secret not in (tmp_path / "curl.log").read_text()


def test_disable_can_explicitly_restore_prior_lan_bind(tmp_path):
    env_file = tmp_path / "app" / ".env"
    _run_config(tmp_path, "status")
    env_file.write_text(env_file.read_text() + "HTTP_BIND_ADDRESS=0.0.0.0\n")
    token_file = tmp_path / "source-token"
    token_file.write_text("valid.token-value\n")
    enabled = _run_config(
        tmp_path,
        "enable",
        "--hostname",
        "lab.example.edu",
        "--team-domain",
        "school.cloudflareaccess.com",
        "--audience",
        "access-audience-1234",
        "--token-file",
        str(token_file),
    )
    assert enabled.returncode == 0, enabled.stderr

    disabled = _run_config(tmp_path, "disable", "--restore-lan-bind")
    assert disabled.returncode == 0, disabled.stderr
    assert "WARNING" in disabled.stderr
    assert "HTTP_BIND_ADDRESS=0.0.0.0" in env_file.read_text()


def test_enable_readiness_failure_restores_environment_and_token(tmp_path):
    _run_config(tmp_path, "status")
    env_file = tmp_path / "app" / ".env"
    before = env_file.read_text()
    installed = tmp_path / "installed-token"
    installed.write_text("old.token.value\n")
    installed.chmod(0o400)
    token_file = tmp_path / "source-token"
    secret = "new.secret.token"
    token_file.write_text(secret + "\n")

    failed = _run_config(
        tmp_path,
        "enable",
        "--hostname",
        "lab.example.edu",
        "--team-domain",
        "school.cloudflareaccess.com",
        "--audience",
        "access-audience-1234",
        "--token-file",
        str(token_file),
        extra_env={"FAKE_CURL_FAIL": "true"},
    )

    assert failed.returncode != 0
    restored = env_file.read_text()
    assert before.strip() in restored
    assert "HTTP_BIND_ADDRESS=127.0.0.1" in restored
    assert installed.read_text() == "old.token.value\n"
    assert secret not in failed.stdout + failed.stderr
    assert secret not in (tmp_path / "docker.log").read_text()
    assert secret not in (tmp_path / "curl.log").read_text()


def test_enable_failure_never_reopens_a_previously_broad_bind(tmp_path):
    _run_config(tmp_path, "status")
    env_file = tmp_path / "app" / ".env"
    env_file.write_text(env_file.read_text() + "HTTP_BIND_ADDRESS=0.0.0.0\n")
    token_file = tmp_path / "source-token"
    token_file.write_text("valid.token.value\n")

    failed = _run_config(
        tmp_path,
        "enable",
        "--hostname",
        "lab.example.edu",
        "--team-domain",
        "school.cloudflareaccess.com",
        "--audience",
        "access-audience-1234",
        "--token-file",
        str(token_file),
        extra_env={"FAKE_CURL_FAIL": "true"},
    )

    assert failed.returncode != 0
    restored = env_file.read_text()
    assert "HTTP_BIND_ADDRESS=0.0.0.0" not in restored
    assert restored.count("HTTP_BIND_ADDRESS=127.0.0.1") == 1


def test_status_json_is_safe_and_machine_readable(tmp_path):
    _run_config(tmp_path, "status")
    env_file = tmp_path / "app" / ".env"
    env_file.write_text(
        env_file.read_text()
        + "CLOUDFLARE_TUNNEL_ENABLED=true\n"
        + "CLOUDFLARE_ACCESS_REQUIRED=true\n"
        + "CLOUDFLARE_PUBLIC_HOSTNAME=lab.example.edu\n"
    )
    secret = "do.not.disclose.this.token"
    installed = tmp_path / "installed-token"
    installed.write_text(secret)
    installed.chmod(0o440)

    result = _run_config(
        tmp_path,
        "status",
        "--json",
        extra_env={"FAKE_CLOUDFLARED_RUNNING": "true"},
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["enabled"] is True
    assert payload["access_required"] is True
    assert payload["public_hostname"] == "lab.example.edu"
    assert payload["token"]["installed"] is True
    assert payload["token"]["size_bytes"] == len(secret)
    assert payload["token"]["mode"] == "440"
    assert payload["container_state"] == "running"
    assert payload["local_ready"] is True
    assert secret not in result.stdout + result.stderr


def test_enable_rejects_invalid_access_domain_without_editing_environment(tmp_path):
    token_file = tmp_path / "source-token"
    token_file.write_text("valid.token-value\n")
    initial = _run_config(tmp_path, "status")
    assert initial.returncode == 0
    env_file = tmp_path / "app" / ".env"
    before = env_file.read_text()

    result = _run_config(
        tmp_path,
        "enable",
        "--hostname",
        "lab.example.edu",
        "--team-domain",
        "attacker.example.com",
        "--audience",
        "access-audience-1234",
        "--token-file",
        str(token_file),
    )

    assert result.returncode != 0
    assert env_file.read_text() == before
