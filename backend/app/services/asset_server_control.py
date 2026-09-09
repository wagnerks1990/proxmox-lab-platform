from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import ProxmoxCluster, ProxmoxHostAccess, ProxmoxNode
from app.services.host_runner import HostRunnerService

Kind = Literal["iso", "ct_template"]


class HostRunnerNotConfiguredError(ValueError):
    pass


@dataclass(frozen=True)
class ServiceSpec:
    service_name: str
    working_directory: str
    default_port: int
    base_url: str | None


SPECS: dict[str, ServiceSpec] = {
    "iso": ServiceSpec(
        "proxmox-lab-iso-server.service",
        "/var/lib/vz/template/iso",
        8088,
        settings.asset_source_iso_base_url,
    ),
    "ct_template": ServiceSpec(
        "proxmox-lab-ct-template-server.service",
        "/var/lib/vz/template/cache",
        8089,
        settings.asset_source_ct_base_url,
    ),
}


class AssetServerControl:
    def __init__(self, db: Session):
        self.db = db

    def _resolve_cluster_id(self, cluster_id: int | None) -> int:
        if cluster_id:
            return int(cluster_id)
        active = (
            self.db.query(ProxmoxCluster)
            .filter(ProxmoxCluster.is_active.is_(True))
            .first()
        )
        if not active:
            raise ValueError("No active Proxmox cluster configured.")
        return int(active.id)

    def _validate_kind(self, kind: str) -> ServiceSpec:
        if kind not in SPECS:
            raise ValueError("kind must be iso or ct_template")
        return SPECS[kind]

    def _resolve_node(self, cluster_id: int, source_node: str | None) -> ProxmoxNode:
        q = self.db.query(ProxmoxNode).filter(ProxmoxNode.cluster_id == cluster_id)
        if source_node:
            q = q.filter(ProxmoxNode.node_name == source_node)
            node = q.first()
        else:
            node = (
                q.filter(
                    ProxmoxNode.node_name == (settings.asset_source_node or "")
                ).first()
                or q.first()
            )
        if not node:
            raise ValueError("No known Proxmox nodes for cluster.")
        if str(getattr(node, "status", "")).lower() not in {"online", "up"}:
            raise ValueError(f"Source node {node.node_name} is not online.")
        return node

    def _resolve_host_access(
        self, cluster_id: int, node_name: str
    ) -> ProxmoxHostAccess:
        if not settings.host_runner_enabled:
            raise HostRunnerNotConfiguredError(
                "Host runner is not configured. Configure Host Access before managing asset services."
            )
        row = (
            self.db.query(ProxmoxHostAccess)
            .filter(
                ProxmoxHostAccess.cluster_id == cluster_id,
                ProxmoxHostAccess.node_name == node_name,
            )
            .first()
        )
        if not row or str(getattr(row, "status", "")).lower() != "host_runner":
            raise HostRunnerNotConfiguredError(
                "Host runner is not configured. Configure Host Access before managing asset services."
            )
        if not getattr(row, "encrypted_private_key", None) and not getattr(
            row, "key_ref", None
        ):
            raise HostRunnerNotConfiguredError(
                "Host runner is not configured. Configure Host Access before managing asset services."
            )
        return row

    def _status_payload(
        self, kind: str, node_name: str, spec: ServiceSpec, status: str, message: str
    ):
        return {
            "kind": kind,
            "source_node": node_name,
            "service_name": spec.service_name,
            "status": status,
            "base_url": spec.base_url,
            "working_directory": spec.working_directory,
            "message": message,
        }

    def _execute_host_runner(self, node_name: str, action: str, kind: str):
        res = HostRunnerService().run_helper(node_name, kind, action)
        out = f"{res.stdout}\n{res.stderr}".lower()
        if action == "status":
            if res.ok and ("active" in out or "running" in out):
                return {"status": "running", "message": "service running"}
            if res.ok and ("inactive" in out or "stopped" in out):
                return {"status": "stopped", "message": "service stopped"}
            if "could not be found" in out or "not-found" in out or "not found" in out:
                return {
                    "status": "not_installed",
                    "message": "service not installed on node",
                }
            return {
                "status": ("error" if not res.ok else "unknown"),
                "message": (res.stderr or res.stdout or "unknown status").strip()[:300],
            }
        if res.ok:
            return {
                "status": "running" if action in {"install", "start"} else "stopped",
                "message": f"{action} completed",
            }
        return {
            "status": "error",
            "message": (res.stderr or res.stdout or f"{action} failed").strip()[:300],
        }

    def status(
        self, kind: str, cluster_id: int | None = None, source_node: str | None = None
    ):
        spec = self._validate_kind(kind)
        cid = self._resolve_cluster_id(cluster_id)
        node = self._resolve_node(cid, source_node)
        try:
            self._resolve_host_access(cid, node.node_name)
        except HostRunnerNotConfiguredError as exc:
            return self._status_payload(
                kind, node.node_name, spec, "not_configured", str(exc)
            )
        run = self._execute_host_runner(
            node_name=node.node_name, action="status", kind=kind
        )
        return self._status_payload(
            kind,
            node.node_name,
            spec,
            run.get("status", "error"),
            run.get("message", "Unknown status."),
        )

    def action(
        self,
        action: str,
        kind: str,
        cluster_id: int | None = None,
        source_node: str | None = None,
        bind_address: str | None = None,
        port: int | None = None,
    ):
        if action not in {"install", "start", "stop"}:
            raise ValueError("unsupported action")
        spec = self._validate_kind(kind)
        cid = self._resolve_cluster_id(cluster_id)
        node = self._resolve_node(cid, source_node)

        if port is not None and int(port) != spec.default_port:
            raise ValueError(f"port must be {spec.default_port} for {kind}")

        if bind_address is not None and spec.base_url:
            expected = (
                spec.base_url.split("://", 1)[-1].split(":", 1)[0].split("/", 1)[0]
            )
            if bind_address != expected:
                raise ValueError(
                    f"bind_address must match configured asset source host ({expected})"
                )

        self._resolve_host_access(cid, node.node_name)
        run = self._execute_host_runner(
            node_name=node.node_name, action=action, kind=kind
        )
        return self._status_payload(
            kind,
            node.node_name,
            spec,
            run.get("status", "error"),
            run.get("message", f"{action} failed."),
        )
