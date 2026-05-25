from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models.models import ProxmoxCluster
from app.services.proxmox import ProxmoxClient


def _pct(used: float | int | None, total: float | int | None) -> float | None:
    if used is None or total in (None, 0):
        return None
    return round((float(used) / float(total)) * 100.0, 2)


def _is_template(vm: dict[str, Any]) -> bool:
    if vm.get('template') in (1, True, '1', 'true', 'True'):
        return True
    return False


def _classify_vm_status(status: str | None) -> str:
    s = (status or '').lower()
    if s == 'running':
        return 'running'
    if s == 'stopped':
        return 'stopped'
    if s in {'paused', 'suspended'}:
        return 'paused'
    return 'unknown'


class ProxmoxResourceStatsService:
    def __init__(self, db: Session):
        self.db = db

    async def active_cluster_stats(self) -> dict[str, Any]:
        cluster = self.db.query(ProxmoxCluster).filter(ProxmoxCluster.is_active.is_(True)).first()
        if cluster:
            return await self.cluster_stats(cluster)

        # env fallback path
        client = ProxmoxClient()
        return await self._collect_from_client(client, cluster=None)

    async def cluster_stats(self, cluster: ProxmoxCluster) -> dict[str, Any]:
        client = ProxmoxClient()
        # Force specific cluster credentials/url for this call if id requested isn't active
        if not cluster.is_active:
            from app.services.secret_crypto import decrypt_secret
            secret = decrypt_secret(cluster.encrypted_token_secret) if cluster.encrypted_token_secret else ''
            client.base_url = cluster.api_url.rstrip('/')
            client.verify_ssl = bool(cluster.verify_ssl)
            client.headers = {'Authorization': f'PVEAPIToken={cluster.token_user}!{cluster.token_id}={secret}'}
            client.config_source = 'database_cluster_by_id'
        return await self._collect_from_client(client, cluster=cluster)

    async def _collect_from_client(self, client: ProxmoxClient, cluster: ProxmoxCluster | None) -> dict[str, Any]:
        warnings: list[str] = []
        fetched_at = datetime.now(timezone.utc).isoformat()

        async with httpx.AsyncClient(verify=client.verify_ssl, timeout=30, headers=client.headers) as http:
            resources_resp = await http.get(f'{client.base_url}/cluster/resources')
            resources_resp.raise_for_status()
            resources = resources_resp.json().get('data', [])

        node_resources = [r for r in resources if r.get('type') == 'node']
        vm_resources = [r for r in resources if r.get('type') == 'qemu']

        node_map: dict[str, dict[str, Any]] = {}
        for n in node_resources:
            name = n.get('node')
            if not name:
                continue
            mem_used = n.get('mem')
            mem_total = n.get('maxmem')
            disk_used = n.get('disk')
            disk_total = n.get('maxdisk')
            cpu_ratio = n.get('cpu')
            cpu_usage_percent = round(float(cpu_ratio) * 100.0, 2) if cpu_ratio is not None else None
            node_map[name] = {
                'name': name,
                'status': n.get('status') or 'unknown',
                'cpu_usage_percent': cpu_usage_percent,
                'cpu_count': n.get('maxcpu'),
                'memory_used_bytes': mem_used,
                'memory_total_bytes': mem_total,
                'memory_usage_percent': _pct(mem_used, mem_total),
                'disk_used_bytes': disk_used,
                'disk_total_bytes': disk_total,
                'disk_usage_percent': _pct(disk_used, disk_total),
                'vm_count': 0,
                'running_vm_count': 0,
                'stopped_vm_count': 0,
                'paused_vm_count': 0,
                'template_count': 0,
                'unknown_vm_count': 0,
                'uptime_seconds': n.get('uptime'),
            }

        totals = {
            'total_vms': 0,
            'running_vms': 0,
            'stopped_vms': 0,
            'paused_vms': 0,
            'templates': 0,
            'unknown_vms': 0,
        }

        for vm in vm_resources:
            node = vm.get('node')
            if node not in node_map:
                warnings.append(f'VM resource references unknown node: {node}')
                continue

            if _is_template(vm):
                node_map[node]['template_count'] += 1
                totals['templates'] += 1
                continue

            node_map[node]['vm_count'] += 1
            totals['total_vms'] += 1

            cls = _classify_vm_status(vm.get('status'))
            if cls == 'running':
                node_map[node]['running_vm_count'] += 1
                totals['running_vms'] += 1
            elif cls == 'stopped':
                node_map[node]['stopped_vm_count'] += 1
                totals['stopped_vms'] += 1
            elif cls == 'paused':
                node_map[node]['paused_vm_count'] += 1
                totals['paused_vms'] += 1
            else:
                node_map[node]['unknown_vm_count'] += 1
                totals['unknown_vms'] += 1

        nodes = sorted(node_map.values(), key=lambda x: x['name'])

        total_mem_used = sum((n.get('memory_used_bytes') or 0) for n in nodes)
        total_mem_total = sum((n.get('memory_total_bytes') or 0) for n in nodes)
        total_disk_used = sum((n.get('disk_used_bytes') or 0) for n in nodes)
        total_disk_total = sum((n.get('disk_total_bytes') or 0) for n in nodes)
        total_cpu_cores = sum((n.get('cpu_count') or 0) for n in nodes)

        online_nodes = len([n for n in nodes if (n.get('status') or '').lower() in {'online', 'up'}])
        cpu_weighted = None
        if total_cpu_cores > 0:
            weighted_sum = sum(((n.get('cpu_usage_percent') or 0.0) * (n.get('cpu_count') or 0)) for n in nodes)
            cpu_weighted = round(weighted_sum / total_cpu_cores, 2)

        summary = {
            'total_nodes': len(nodes),
            'online_nodes': online_nodes,
            'offline_nodes': len(nodes) - online_nodes,
            'total_cpu_cores': total_cpu_cores,
            'cpu_usage_percent': cpu_weighted,
            'memory_used_bytes': total_mem_used,
            'memory_total_bytes': total_mem_total,
            'memory_usage_percent': _pct(total_mem_used, total_mem_total),
            'disk_used_bytes': total_disk_used,
            'disk_total_bytes': total_disk_total,
            'disk_usage_percent': _pct(total_disk_used, total_disk_total),
            **totals,
        }

        return {
            'config_source': getattr(client, 'config_source', 'not_configured'),
            'cluster': {
                'id': getattr(cluster, 'id', None),
                'name': getattr(cluster, 'name', None),
                'api_url': getattr(cluster, 'api_url', None) or client.base_url,
            },
            'summary': summary,
            'nodes': nodes,
            'warnings': sorted(set(warnings)),
            'fetched_at': fetched_at,
        }
