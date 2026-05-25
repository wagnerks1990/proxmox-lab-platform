from __future__ import annotations

import subprocess
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class HostRunnerResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str


class HostRunnerService:
    HELPER = '/usr/local/sbin/proxmox-lab-asset-server'

    def __init__(self):
        self.user = settings.host_runner_user
        self.key_path = settings.host_runner_private_key_path

    def ensure_ready(self):
        if not settings.host_runner_enabled:
            raise ValueError('Host runner is disabled.')
        if not self.key_path:
            raise ValueError('HOST_RUNNER_PRIVATE_KEY_PATH is not configured.')

    def run_helper(self, node: str, kind: str, action: str) -> HostRunnerResult:
        if kind not in {'iso', 'ct_template'}:
            raise ValueError('kind must be iso or ct_template')
        if action not in {'status', 'install', 'start', 'stop'}:
            raise ValueError('unsupported action')
        self.ensure_ready()
        cmd = [
            'ssh',
            '-i',
            self.key_path,
            '-o',
            'BatchMode=yes',
            '-o',
            'StrictHostKeyChecking=accept-new',
            f'{self.user}@{node}',
            'sudo',
            self.HELPER,
            kind,
            action,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        return HostRunnerResult(
            ok=proc.returncode == 0,
            returncode=proc.returncode,
            stdout=proc.stdout or '',
            stderr=proc.stderr or '',
        )
