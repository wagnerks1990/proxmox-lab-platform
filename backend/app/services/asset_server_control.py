from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import ProxmoxCluster, ProxmoxHostAccess, ProxmoxNode

Kind = Literal['iso', 'ct_template']


@dataclass
class ServiceSpec:
    service_name: str
    working_directory: str
    default_port: int
    base_url: str | None


SPECS: dict[str, ServiceSpec] = {
    'iso': ServiceSpec('proxmox-lab-iso-server.service', '/var/lib/vz/template/iso', 8088, settings.asset_source_iso_base_url),
    'ct_template': ServiceSpec('proxmox-lab-ct-template-server.service', '/var/lib/vz/template/cache', 8089, settings.asset_source_ct_base_url),
}


class AssetServerControl:
    def __init__(self, db: Session):
        self.db = db

    def _resolve_cluster_id(self, cluster_id: int | None) -> int:
        if cluster_id:
            return int(cluster_id)
        active = self.db.query(ProxmoxCluster).filter(ProxmoxCluster.is_active.is_(True)).first()
        if not active:
            raise ValueError('No active Proxmox cluster configured.')
        return int(active.id)

    def _validate_kind(self, kind: str) -> ServiceSpec:
        if kind not in SPECS:
            raise ValueError('kind must be iso or ct_template')
        return SPECS[kind]

    def _resolve_node(self, cluster_id: int, source_node: str | None) -> ProxmoxNode:
        q = self.db.query(ProxmoxNode).filter(ProxmoxNode.cluster_id == cluster_id)
        if source_node:
            q = q.filter(ProxmoxNode.node_name == source_node)
            node = q.first()
        else:
            node = q.filter(ProxmoxNode.node_name == (settings.asset_source_node or '')).first() or q.first()
        if not node:
            raise ValueError('No known Proxmox nodes for cluster.')
        return node

    def _host_runner_configured(self, cluster_id: int, node_name: str) -> bool:
        if not settings.host_runner_enabled:
            return False
        row = self.db.query(ProxmoxHostAccess).filter(
            ProxmoxHostAccess.cluster_id == cluster_id,
            ProxmoxHostAccess.node_name == node_name,
            ProxmoxHostAccess.status == 'host_runner',
        ).first()
        return bool(row)

    def status(self, kind: str, cluster_id: int | None = None, source_node: str | None = None):
        spec = self._validate_kind(kind)
        cid = self._resolve_cluster_id(cluster_id)
        node = self._resolve_node(cid, source_node)
        if not self._host_runner_configured(cid, node.node_name):
            return {
                'kind': kind,
                'source_node': node.node_name,
                'service_name': spec.service_name,
                'status': 'not_configured',
                'base_url': spec.base_url,
                'working_directory': spec.working_directory,
                'message': 'Host runner not configured for this node.',
            }
        return {
            'kind': kind,
            'source_node': node.node_name,
            'service_name': spec.service_name,
            'status': 'unsupported',
            'base_url': spec.base_url,
            'working_directory': spec.working_directory,
            'message': 'Host runner command execution path is not enabled in this environment.',
        }

    def action(self, action: str, kind: str, cluster_id: int | None = None, source_node: str | None = None, bind_address: str | None = None, port: int | None = None):
        spec = self._validate_kind(kind)
        cid = self._resolve_cluster_id(cluster_id)
        node = self._resolve_node(cid, source_node)
        allowed_port = spec.default_port
        if port is not None and int(port) != allowed_port:
            raise ValueError(f'port must be {allowed_port} for {kind}')
        if not self._host_runner_configured(cid, node.node_name):
            return {
                'kind': kind,
                'source_node': node.node_name,
                'service_name': spec.service_name,
                'status': 'not_configured',
                'base_url': spec.base_url,
                'working_directory': spec.working_directory,
                'message': 'Host runner not configured. Configure Host Access in Proxmox Setup first.',
            }
        return {
            'kind': kind,
            'source_node': node.node_name,
            'service_name': spec.service_name,
            'status': 'unsupported',
            'base_url': spec.base_url,
            'working_directory': spec.working_directory,
            'message': f'{action} is blocked: command runner execution path is not enabled.',
        }
