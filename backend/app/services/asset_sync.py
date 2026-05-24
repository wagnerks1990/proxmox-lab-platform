from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.models import AssetCatalog, AssetNodeState, AssetSyncJob, AssetSyncJobEvent
from app.services.proxmox_assets import ProxmoxAssetsService

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
        job = AssetSyncJob(asset_id=asset_id, target_node=target_node, state='queued', method=method, metadata_json=str(meta), started_at=datetime.utcnow())
        self.db.add(job)
        self.db.flush()
        return job

    def _log(self, job_id: int, level: str, message: str, meta: dict | None = None):
        self.db.add(AssetSyncJobEvent(job_id=job_id, level=level, message=message, metadata_json=str(meta or {})))

    async def sync_iso(self, filename: str, storage_id: str, source_url: str, target_nodes: list[str]):
        self._validate_url(source_url)
        await self._validate_targets(target_nodes, storage_id)
        jobs = []
        for node in target_nodes:
            job = self._new_job('download-url-iso', node)
            current = await self.assets.discover_isos_by_node([node], storage_id)
            have = any((x.get('filename') == filename) for x in (current[0].get('items') if current else []))
            if have:
                job.state = 'verified'
                self._log(job.id, 'info', f'ISO already present on {node}; verified idempotently.')
                jobs.append(job)
                continue
            self._log(job.id, 'info', f'Starting ISO sync for {filename} to {node}')
            upid = await self.assets.download_url(node, storage_id, 'iso', filename, source_url)
            job.proxmox_upid = str(upid)
            job.state = 'syncing'
            self._log(job.id, 'info', 'Download URL submitted', {'upid': job.proxmox_upid})
            # best-effort verify immediately for MVP hardening (live deploy can poll longer)
            current_after = await self.assets.discover_isos_by_node([node], storage_id)
            have_after = any((x.get('filename') == filename) for x in (current_after[0].get('items') if current_after else []))
            if have_after:
                job.state = 'verified'
                self._log(job.id, 'info', 'ISO verified on target node.')
            else:
                job.state = 'failed'
                job.error = 'ISO not verified after download-url submission.'
                self._log(job.id, 'error', job.error)
            jobs.append(job)
        self.db.commit()
        return jobs

    async def sync_ct_template(self, filename: str, storage_id: str, source_url: str, target_nodes: list[str]):
        self._validate_url(source_url)
        await self._validate_targets(target_nodes, storage_id)
        jobs = []
        for node in target_nodes:
            job = self._new_job('download-url-vztmpl', node)
            current = await self.assets.discover_ct_templates_by_node([node], storage_id)
            have = any((x.get('filename') == filename) for x in (current[0].get('items') if current else []))
            if have:
                job.state = 'verified'
                self._log(job.id, 'info', f'CT template already present on {node}; verified idempotently.')
                jobs.append(job)
                continue
            self._log(job.id, 'info', f'Starting CT template sync for {filename} to {node}')
            upid = await self.assets.download_url(node, storage_id, 'vztmpl', filename, source_url)
            job.proxmox_upid = str(upid)
            job.state = 'syncing'
            self._log(job.id, 'info', 'Download URL submitted', {'upid': job.proxmox_upid})
            current_after = await self.assets.discover_ct_templates_by_node([node], storage_id)
            have_after = any((x.get('filename') == filename) for x in (current_after[0].get('items') if current_after else []))
            if have_after:
                job.state = 'verified'
                self._log(job.id, 'info', 'CT template verified on target node.')
            else:
                job.state = 'failed'
                job.error = 'CT template not verified after download-url submission.'
                self._log(job.id, 'error', job.error)
            jobs.append(job)
        self.db.commit()
        return jobs

    async def sync_vm_template(self, source_node: str, source_vmid: int, template_name: str, storage_id: str, target_nodes: list[str]):
        # Guarded unsupported until command-runner is configured.
        jobs = []
        for node in target_nodes:
            job = self._new_job('local_clone_migrate_template', node, source_node=source_node, source_vmid=source_vmid)
            job.state = 'failed'
            job.error = 'VM template sync requires configured command runner (qm/pvesh) and is not enabled in this environment.'
            self._log(job.id, 'error', job.error, {'template_name': template_name, 'storage_id': storage_id})
            jobs.append(job)
        self.db.commit()
        return jobs
