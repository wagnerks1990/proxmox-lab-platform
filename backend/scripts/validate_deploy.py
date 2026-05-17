#!/usr/bin/env python3
"""Post-pull deployment validation for current live backend health.

This script validates current state only; it intentionally does not inspect historical
journal logs, so stale crash traces from prior restarts do not affect results.
"""

from __future__ import annotations

import asyncio
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path

import httpx
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / 'backend'


class CheckFailure(RuntimeError):
    pass


def _load_dotenv_if_present() -> None:
    env_path = BACKEND_DIR / '.env'
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def check_required_settings_present() -> None:
    required = [
        'DATABASE_URL',
        'JWT_SECRET_KEY',
        'PROXMOX_BASE_URL',
        'PROXMOX_TOKEN_ID',
        'PROXMOX_TOKEN_SECRET',
    ]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        fail('environment settings', f'missing required settings: {", ".join(missing)}')
    ok('environment settings', 'required settings are present')


def ok(name: str, detail: str) -> None:
    print(f"[OK] {name}: {detail}")


def fail(name: str, detail: str) -> None:
    raise CheckFailure(f"[FAIL] {name}: {detail}")


def check_imports_compile() -> None:
    failed: list[str] = []
    for file_path in (BACKEND_DIR / 'app').rglob('*.py'):
        try:
            py_compile.compile(str(file_path), doraise=True)
        except py_compile.PyCompileError as exc:
            failed.append(f"{file_path.relative_to(ROOT)} -> {exc.msg}")
    if failed:
        fail('python compile', '; '.join(failed[:3]))
    ok('python compile', 'all backend app modules compile')


def check_session_expired_symbol() -> None:
    from app.architecture import events

    value = getattr(events, 'SESSION_EXPIRED', None)
    if value != 'SESSION_EXPIRED':
        fail('SESSION_EXPIRED symbol', f"expected 'SESSION_EXPIRED', got {value!r}")
    ok('SESSION_EXPIRED symbol', "present in app.architecture.events")


def check_alembic_single_head() -> None:
    cfg = Config(str(BACKEND_DIR / 'alembic.ini'))
    cfg.set_main_option('script_location', str(BACKEND_DIR / 'alembic'))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    if len(heads) != 1:
        fail('alembic heads', f'expected one head, found {heads}')

    cmd = ['alembic', '-c', str(BACKEND_DIR / 'alembic.ini'), 'heads']
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        fail('alembic cli', result.stderr.strip() or result.stdout.strip() or 'unknown error')
    ok('alembic heads', result.stdout.strip())


def check_database_connectivity() -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        db.execute(text('SELECT 1'))
    except Exception as exc:  # noqa: BLE001
        fail('database connectivity', str(exc))
    finally:
        db.close()
    ok('database connectivity', 'SELECT 1 succeeded')


async def check_health_endpoint() -> None:
    url = 'http://127.0.0.1:8000/api/health'
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
    except Exception as exc:  # noqa: BLE001
        fail('/api/health', f'request failed: {exc}')

    if response.status_code != 200:
        fail('/api/health', f'unexpected status {response.status_code}: {response.text}')

    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        fail('/api/health', f'invalid json: {exc}')

    if payload.get('backend') != 'ok':
        fail('/api/health', f"backend not ok: {payload}")

    if not payload.get('database', {}).get('ok'):
        fail('/api/health', f"database not ok: {payload}")

    if not payload.get('proxmox', {}).get('ok'):
        fail('/api/health', f"proxmox not ok: {payload}")

    ok('/api/health', json.dumps(payload, separators=(',', ':')))


async def main() -> int:
    os.chdir(BACKEND_DIR)
    sys.path.insert(0, str(BACKEND_DIR))

    _load_dotenv_if_present()

    checks = [
        ('environment settings', check_required_settings_present),
        ('python compile', check_imports_compile),
        ('SESSION_EXPIRED symbol', check_session_expired_symbol),
        ('alembic heads', check_alembic_single_head),
        ('database connectivity', check_database_connectivity),
    ]

    try:
        for _name, fn in checks:
            fn()
        await check_health_endpoint()
    except CheckFailure as exc:
        print(exc)
        print('\nDeployment validation FAILED.')
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f'[FAIL] unexpected error: {exc}')
        print('\nDeployment validation FAILED.')
        return 1

    print('\nDeployment validation PASSED.')
    print('Note: this validates live state and does not treat stale historical journal logs as active failures.')
    return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
