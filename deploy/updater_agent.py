#!/usr/bin/env python3
"""Minimal root-owned deployment agent exposed only through a Unix socket."""

from __future__ import annotations

import fcntl
import hmac
import json
import os
import re
import socket
import subprocess
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


APP_DIR = Path(os.environ.get('PLATFORM_APP_DIR', '/opt/proxmox-lab-platform/app')).resolve()
STATE_DIR = Path(os.environ.get('PLATFORM_STATE_DIR', '/var/lib/proxmox-lab-platform'))
SOCKET_PATH = Path(os.environ.get('UPDATER_SOCKET_PATH', '/run/proxmox-lab-updater/updater.sock'))
TOKEN = os.environ.get('UPDATER_TOKEN', '')
UPDATER_GID = int(os.environ.get('UPDATER_GID', '0'))
ALLOWED_REPOSITORY = os.environ.get('UPDATER_REPOSITORY', 'https://github.com/wagnerks1990/proxmox-lab-platform.git')
HEALTH_URL = os.environ.get('PLATFORM_HEALTH_URL', 'http://127.0.0.1:8080/api/ready')
REF_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._/-]{0,119}$')
SHA_RE = re.compile(r'^[0-9a-f]{40}$')
REQUIRE_SIGNED_COMMITS = os.environ.get('UPDATER_REQUIRE_SIGNED_COMMITS', 'false').lower() == 'true'


def run(args: list[str], *, check: bool = True, stdout=None, input_file=None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=APP_DIR, check=check, text=input_file is None, stdout=stdout, stdin=input_file, stderr=subprocess.PIPE)


def commit(ref: str = 'HEAD') -> str:
    return run(['git', 'rev-parse', '--verify', f'{ref}^{{commit}}'], stdout=subprocess.PIPE).stdout.strip()


def normalize_repo(value: str) -> str:
    return value.strip().rstrip('/').removesuffix('.git')


def validate_request(payload: dict) -> tuple[str, str]:
    repository = str(payload.get('repository') or ALLOWED_REPOSITORY)
    branch = str(payload.get('branch') or 'main')
    if normalize_repo(repository) != normalize_repo(ALLOWED_REPOSITORY):
        raise ValueError('Repository is not allowed by the host configuration')
    if not REF_RE.fullmatch(branch) or '..' in branch:
        raise ValueError('Invalid Git reference')
    return repository, branch


def compose(*args: str, check: bool = True, stdout=None, input_file=None):
    return run(['docker', 'compose', '--env-file', str(APP_DIR / '.env'), *args], check=check, stdout=stdout, input_file=input_file)


def env_file() -> dict[str, str]:
    values = {}
    for raw in (APP_DIR / '.env').read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            values[key] = value
    return values


def backup_database(from_version: str) -> Path:
    STATE_DIR.joinpath('backups').mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path = STATE_DIR / 'backups' / f'before-{from_version[:12]}-{stamp}.dump'
    env = env_file()
    with path.open('wb') as handle:
        compose('exec', '-T', 'postgres', 'pg_dump', '-Fc', '-U', env.get('POSTGRES_USER', 'proxmox_lab'), '-d', env.get('POSTGRES_DB', 'proxmox_lab'), stdout=handle)
    os.chmod(path, 0o600)
    return path


def restore_database(path: Path) -> None:
    if not path.is_file() or not str(path.resolve()).startswith(str(STATE_DIR.resolve())):
        raise RuntimeError('Rollback backup is missing or outside the state directory')
    env = env_file()
    compose('stop', 'api', 'web', check=False)
    with path.open('rb') as handle:
        compose('exec', '-T', 'postgres', 'pg_restore', '--clean', '--if-exists', '--no-owner', '-U', env.get('POSTGRES_USER', 'proxmox_lab'), '-d', env.get('POSTGRES_DB', 'proxmox_lab'), input_file=handle)


def wait_for_health(timeout: int = 180) -> None:
    deadline = time.monotonic() + timeout
    error = 'health check did not run'
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=5) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            error = str(exc)
        time.sleep(3)
    raise RuntimeError(f'Health gate failed: {error}')


def write_state(data: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    temporary = STATE_DIR / 'update-state.tmp'
    temporary.write_text(json.dumps(data, indent=2))
    os.chmod(temporary, 0o600)
    temporary.replace(STATE_DIR / 'update-state.json')


def read_state() -> dict:
    path = STATE_DIR / 'update-state.json'
    return json.loads(path.read_text()) if path.exists() else {}


def check_update(payload: dict) -> dict:
    _, branch = validate_request(payload)
    run(['git', 'fetch', '--prune', 'origin'])
    current = commit()
    target = commit(f'origin/{branch}') if not payload.get('target_ref') else commit(branch)
    return {'ok': True, 'update_available': current != target, 'from_version': current, 'to_version': target, 'message': 'Update available' if current != target else 'Already current'}


def apply_update(payload: dict) -> dict:
    _, branch = validate_request(payload)
    requested = str(payload.get('target_ref') or '')
    if not SHA_RE.fullmatch(requested):
        raise ValueError('target_ref must be the exact 40-character commit SHA returned by the update check')
    if run(['git', 'status', '--porcelain'], stdout=subprocess.PIPE).stdout.strip():
        raise RuntimeError('Deployment checkout has local changes; refusing to overwrite them')
    run(['git', 'fetch', '--prune', 'origin'])
    previous = commit()
    target = commit(requested)
    if run(['git', 'merge-base', '--is-ancestor', target, f'origin/{branch}'], check=False).returncode != 0:
        raise RuntimeError('Requested commit is not reachable from the configured update branch')
    if REQUIRE_SIGNED_COMMITS:
        run(['git', 'verify-commit', target])
    if previous == target:
        return {'ok': True, 'from_version': previous, 'to_version': target, 'message': 'Already current'}
    backup = backup_database(previous)
    state = {'previous_version': previous, 'current_version': target, 'backup_path': str(backup), 'updated_at': datetime.now(timezone.utc).isoformat()}
    try:
        run(['git', 'checkout', '--detach', target])
        compose('build', '--pull')
        compose('up', '-d', '--remove-orphans')
        wait_for_health()
        write_state(state)
        return {'ok': True, 'from_version': previous, 'to_version': target, 'backup_path': str(backup), 'message': 'Update applied and health gate passed'}
    except Exception:
        run(['git', 'checkout', '--detach', previous], check=False)
        restore_database(backup)
        compose('up', '-d', '--build', '--remove-orphans', check=False)
        raise


def rollback_update(_payload: dict) -> dict:
    state = read_state()
    target = state.get('previous_version')
    backup = Path(state.get('backup_path', ''))
    if not target:
        raise RuntimeError('No previous successful update is available')
    current = commit()
    reverse_backup = backup_database(current)
    run(['git', 'checkout', '--detach', target])
    compose('build')
    restore_database(backup)
    compose('up', '-d', '--remove-orphans')
    wait_for_health()
    write_state({'previous_version': current, 'current_version': target, 'backup_path': str(reverse_backup), 'rolled_back_at': datetime.now(timezone.utc).isoformat()})
    return {'ok': True, 'from_version': current, 'to_version': target, 'backup_path': str(backup), 'message': 'Application and database rollback completed'}


class UnixHTTPServer(HTTPServer):
    address_family = socket.AF_UNIX


class Handler(BaseHTTPRequestHandler):
    def _reply(self, status: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        supplied = self.headers.get('X-Updater-Token', '')
        return bool(TOKEN) and hmac.compare_digest(supplied, TOKEN)

    def do_GET(self):
        if not self._authorized():
            return self._reply(401, {'ok': False, 'message': 'Unauthorized'})
        if self.path != '/v1/status':
            return self._reply(404, {'ok': False, 'message': 'Not found'})
        state = read_state()
        self._reply(200, {'ok': True, 'available': True, 'current_version': commit(), 'previous_version': state.get('previous_version'), 'backup_path': state.get('backup_path'), 'operation': state.get('operation'), 'signed_commits_required': REQUIRE_SIGNED_COMMITS})

    def do_POST(self):
        if not self._authorized():
            return self._reply(401, {'ok': False, 'message': 'Unauthorized'})
        try:
            length = min(int(self.headers.get('Content-Length', '0')), 16384)
            payload = json.loads(self.rfile.read(length) or b'{}')
            action = {'/v1/check': check_update, '/v1/apply': apply_update, '/v1/rollback': rollback_update}.get(self.path)
            if action is None:
                return self._reply(404, {'ok': False, 'message': 'Not found'})
            if self.path == '/v1/check':
                return self._reply(200, action(payload))
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            current_operation = read_state().get('operation') or {}
            if current_operation.get('status') in {'queued', 'running'}:
                return self._reply(409, {'ok': False, 'message': 'Another update operation is running'})
            lock_path = STATE_DIR / 'update.lock'
            with lock_path.open('w') as probe:
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            operation_id = f'{int(time.time())}-{os.getpid()}'
            state = read_state()
            state['operation'] = {'id': operation_id, 'action': self.path.rsplit('/', 1)[-1], 'status': 'queued', 'started_at': datetime.now(timezone.utc).isoformat()}
            write_state(state)
            threading.Thread(target=_run_async_action, args=(operation_id, action, payload), daemon=True).start()
            self._reply(202, {'ok': True, 'accepted': True, 'operation_id': operation_id, 'message': 'Update operation accepted; poll updater status'})
        except BlockingIOError:
            self._reply(409, {'ok': False, 'message': 'Another update operation is running'})
        except Exception as exc:
            self._reply(500, {'ok': False, 'message': str(exc)})

    def log_message(self, fmt, *args):
        print(f'{self.log_date_time_string()} {fmt % args}', flush=True)


def _run_async_action(operation_id: str, action, payload: dict) -> None:
    try:
        with (STATE_DIR / 'update.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            state = read_state()
            state['operation'] = {**state.get('operation', {}), 'id': operation_id, 'status': 'running'}
            write_state(state)
            try:
                result = action(payload)
                state = read_state()
                state['operation'] = {'id': operation_id, 'status': 'succeeded', 'result': result, 'finished_at': datetime.now(timezone.utc).isoformat()}
            except Exception as exc:
                state = read_state()
                state['operation'] = {'id': operation_id, 'status': 'failed', 'error': str(exc), 'finished_at': datetime.now(timezone.utc).isoformat()}
            write_state(state)
    except Exception as exc:
        state = read_state()
        state['operation'] = {'id': operation_id, 'status': 'failed', 'error': str(exc), 'finished_at': datetime.now(timezone.utc).isoformat()}
        write_state(state)


def main() -> None:
    if os.geteuid() != 0:
        raise SystemExit('Updater must run as root')
    if not TOKEN:
        raise SystemExit('UPDATER_TOKEN is required')
    if not APP_DIR.joinpath('.git').is_dir():
        raise SystemExit(f'Deployment checkout not found: {APP_DIR}')
    SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)
    SOCKET_PATH.unlink(missing_ok=True)
    server = UnixHTTPServer(str(SOCKET_PATH), Handler)
    os.chown(SOCKET_PATH, 0, UPDATER_GID)
    os.chmod(SOCKET_PATH, 0o660)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        SOCKET_PATH.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
