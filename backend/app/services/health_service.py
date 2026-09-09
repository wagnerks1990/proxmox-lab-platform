from sqlalchemy import text
from sqlalchemy.orm import Session
from app.services.proxmox import ProxmoxClient
from app.models.models import ProxmoxCluster, ProxmoxNode, ProxmoxClusterDefault


async def health_summary(db: Session):
    db_ok = True
    pmx_ok = True
    db_error = None
    pmx_error = None
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_ok = False
        db_error = str(exc)
    active_cluster = (
        db.query(ProxmoxCluster).filter(ProxmoxCluster.is_active.is_(True)).first()
    )
    defaults = (
        db.query(ProxmoxClusterDefault)
        .filter(ProxmoxClusterDefault.cluster_id == active_cluster.id)
        .first()
        if active_cluster
        else None
    )
    online_count = (
        db.query(ProxmoxNode)
        .filter(
            ProxmoxNode.cluster_id == active_cluster.id,
            ProxmoxNode.status.in_(["online", "up"]),
        )
        .count()
        if active_cluster
        else 0
    )
    try:
        client = ProxmoxClient()
        nodes = await client.list_nodes()
    except Exception as exc:
        pmx_ok = False
        pmx_error = str(exc)
        client = None
        nodes = []
    return {
        "backend": "ok",
        "database": {"ok": db_ok, "error": db_error},
        "proxmox": {
            "ok": pmx_ok,
            "error": pmx_error,
            "config_source": getattr(client, "config_source", "not_configured"),
            "nodes_discovered_count": len(nodes),
            "credential_status": "present" if pmx_ok or client else "missing",
            "active_cluster_name": getattr(active_cluster, "name", None),
            "online_node_count": online_count,
            "placement_policy": getattr(defaults, "placement_policy", None),
            "default_node": getattr(defaults, "default_node", None),
            "default_storage": getattr(defaults, "default_storage", None),
            "default_bridge": getattr(defaults, "default_bridge", None),
            "default_template_vmid": getattr(defaults, "default_template_vmid", None),
        },
    }
