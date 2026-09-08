from __future__ import annotations

import asyncio
import ast
import json
import math
from datetime import datetime
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.models import AssetSyncJob, AssetSyncJobEvent
from app.services.proxmox_assets import ProxmoxAssetsService
from app.db.session import SessionLocal
from app.core.config import settings

ALLOWED_HOSTS = {'10.0.16.126', '127.0.0.1', 'localhost'}

class AssetSyncService:
    def __init__(self, db: Session):
        self.db = db
        self.assets = ProxmoxAssetsService()

    def _validate_url(self, source_url: str):
        p = urlparse(source_url)
        if p.scheme not in {'http', 'https'}:
            raise ValueError('source_url must use http/https')
        if p.username or p.password:
            raise ValueError('source_url must not include credentials')
        if p.hostname not in ALLOWED_HOSTS:
            raise ValueError(f'source_url host not allowlisted: {p.hostname}')

    async def _validate_targets(self, target_nodes: list[str], storage_id: str):
        nodes = await self.assets.discover_nodes()
        node_map = {n.get('node'): (n.get('status') or '').lower() for n in nodes}
        for n in target_nodes:
            if n not in node_map:
                raise ValueError(f'unknown target node: {n}')
            if node_map[n] not in {'online', 'up'}:
                raise ValueError(f'target node offline: {n}')
            stor = await self.assets._get(f'/nodes/{n}/storage')
            if not any(s.get('storage') == storage_id for s in stor):
                raise ValueError(f'storage {storage_id} missing on node {n}')

    def _new_job(self, method: str, target_node: str, asset_id: int | None = None, **meta):
        job = AssetSyncJob(asset_id=asset_id, target_node=target_node, state='queued', method=method, metadata_json=json.dumps(meta, sort_keys=True), started_at=datetime.utcnow())
        self.db.add(job)
        self.db.flush()
        return job

    def _log(self, job_id: int, level: str, message: str, meta: dict | None = None):
        self.db.add(AssetSyncJobEvent(job_id=job_id, level=level, message=message, metadata_json=json.dumps(meta or {}, sort_keys=True)))

    def _finish(self, job: AssetSyncJob, state: str, error: str | None = None):
        job.state = state
        job.error = error
        job.finished_at = datetime.utcnow()

    async def _sleep(self, seconds: int):
        await asyncio.sleep(seconds)

    async def _poll_task_until_done(self, job: AssetSyncJob, node: str, upid: str):
        poll_interval = max(1, int(settings.asset_sync_poll_interval_seconds or 3))
        timeout_seconds = max(poll_interval, int(settings.asset_sync_download_timeout_seconds or 7200))
        attempt = 0
        latest_task_status = 'unknown'
        latest_exitstatus = None

        max_attempts = max(1, math.ceil(timeout_seconds / poll_interval))
        while attempt < max_attempts:
            attempt += 1
            status = await self.assets.task_status(node, upid)
            task_status = str((status or {}).get('status') or '').lower()
            exitstatus = (status or {}).get('exitstatus')
            latest_task_status = task_status or latest_task_status
            latest_exitstatus = exitstatus
            elapsed = min(timeout_seconds, attempt * poll_interval)
            self._log(job.id, 'info', 'Polling task status', {
                'attempt': attempt,
                'status': task_status,
                'exitstatus': exitstatus,
                'elapsed_seconds': elapsed,
                'timeout_seconds': timeout_seconds,
            })
            if task_status == 'stopped':
                if str(exitstatus).upper() == 'OK':
                    self._log(job.id, 'info', 'Task completed OK', {'exitstatus': exitstatus, 'elapsed_seconds': elapsed, 'timeout_seconds': timeout_seconds})
                    return True, None
                self._log(job.id, 'error', 'Task failed', {'exitstatus': exitstatus, 'elapsed_seconds': elapsed, 'timeout_seconds': timeout_seconds})
                return False, f'Proxmox task failed: {exitstatus or "unknown"}'
            await self._sleep(poll_interval)

        elapsed_total = timeout_seconds
        self._log(job.id, 'error', 'Task polling timeout', {
            'elapsed_seconds': elapsed_total,
            'timeout_seconds': timeout_seconds,
            'latest_task_status': latest_task_status,
            'latest_exitstatus': latest_exitstatus,
        })
        return False, f'Timed out waiting for Proxmox download task to complete (elapsed={elapsed_total}s timeout={timeout_seconds}s latest_status={latest_task_status}).'

    async def _verify_on_node(self, kind: str, filename: str, node: str, storage_id: str):
        if kind == 'iso':
            current = await self.assets.discover_isos_by_node([node], storage_id)
        else:
            current = await self.assets.discover_ct_templates_by_node([node], storage_id)
        return any((x.get('filename') == filename) for x in (current[0].get('items') if current else []))

    async def enqueue_iso(self, filename: str, storage_id: str, source_url: str, target_nodes: list[str]):
        self._validate_url(source_url)
        await self._validate_targets(target_nodes, storage_id)
        jobs = []
        for node in target_nodes:
            job = self._new_job('download-url-iso', node, filename=filename, storage_id=storage_id, source_url=source_url)
            self._log(job.id, 'info', 'Job queued', {'filename': filename, 'storage_id': storage_id})
            jobs.append(job)
        self.db.commit()
        return jobs

    async def enqueue_ct_template(self, filename: str, storage_id: str, source_url: str, target_nodes: list[str]):
        self._validate_url(source_url)
        await self._validate_targets(target_nodes, storage_id)
        jobs = []
        for node in target_nodes:
            job = self._new_job('download-url-vztmpl', node, filename=filename, storage_id=storage_id, source_url=source_url)
            self._log(job.id, 'info', 'Job queued', {'filename': filename, 'storage_id': storage_id})
            jobs.append(job)
        self.db.commit()
        return jobs

    @staticmethod
    async def process_job(job_id: int):
        db = SessionLocal()
        try:
            svc = AssetSyncService(db)
            job = db.query(AssetSyncJob).filter(AssetSyncJob.id == job_id).first()
            if not job:
                return
            try:
                meta = json.loads(job.metadata_json) if job.metadata_json else {}
            except json.JSONDecodeError:
                # Read-only compatibility for jobs queued before metadata became JSON.
                meta = ast.literal_eval(job.metadata_json)
            if not isinstance(meta, dict):
                raise ValueError('Job metadata must be a JSON object')
            filename = meta.get('filename')
            storage_id = meta.get('storage_id', 'local')
            source_url = meta.get('source_url')
            node = job.target_node

            if job.method == 'download-url-iso':
                current = await svc.assets.discover_isos_by_node([node], storage_id)
                have = any((x.get('filename') == filename) for x in (current[0].get('items') if current else []))
                if have:
                    svc._finish(job, 'verified')
                    svc._log(job.id, 'info', f'ISO already present on {node}; verified idempotently.')
                    db.commit(); return
                upid = await svc.assets.download_url(node, storage_id, 'iso', filename, source_url)
            else:
                current = await svc.assets.discover_ct_templates_by_node([node], storage_id)
                have = any((x.get('filename') == filename) for x in (current[0].get('items') if current else []))
                if have:
                    svc._finish(job, 'verified')
                    svc._log(job.id, 'info', f'CT template already present on {node}; verified idempotently.')
                    db.commit(); return
                upid = await svc.assets.download_url(node, storage_id, 'vztmpl', filename, source_url)

            job.proxmox_upid = str(upid)
            job.state = 'syncing'
            svc._log(job.id, 'info', 'download-url submitted', {'upid': job.proxmox_upid})
            db.commit()

            ok, err = await svc._poll_task_until_done(job, node, job.proxmox_upid)
            if not ok:
                svc._finish(job, 'failed', err)
                db.commit(); return
            have_after = await svc._verify_on_node('iso' if job.method == 'download-url-iso' else 'ct_template', filename, node, storage_id)
            if have_after:
                svc._finish(job, 'verified')
                svc._log(job.id, 'info', 'verification passed')
            else:
                svc._finish(job, 'failed', 'Post-download verification failed.')
                svc._log(job.id, 'error', 'verification failed')
            db.commit()
        except Exception as e:
            job = db.query(AssetSyncJob).filter(AssetSyncJob.id == job_id).first()
            if job:
                svc = AssetSyncService(db)
                svc._finish(job, 'failed', str(e)[:300])
                svc._log(job.id, 'error', 'task failed', {'error': str(e)[:300]})
                db.commit()
        finally:
            db.close()

    async def sync_vm_template(self, source_node: str, source_vmid: int, template_name: str, storage_id: str, target_nodes: list[str]):
        # Guarded unsupported until command-runner is configured.
        jobs = []
        for node in target_nodes:
            job = self._new_job('local_clone_migrate_template', node, source_node=source_node, source_vmid=source_vmid)
            self._finish(job, 'failed', 'VM template sync requires configured command runner (qm/pvesh) and is not enabled in this environment.')
            self._log(job.id, 'error', job.error, {'template_name': template_name, 'storage_id': storage_id})
            jobs.append(job)
        self.db.commit()
        return jobs
