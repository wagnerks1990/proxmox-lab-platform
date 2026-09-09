from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PlacementDecision:
    selected_node: str
    reason: str
    details: dict[str, Any]


class PlacementError(Exception):
    pass


def _is_online(node: dict[str, Any]) -> bool:
    return (node.get("status") or "").lower() in {"online", "up"}


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _score(
    node: dict[str, Any], running_vm_count: int
) -> tuple[float, float, int, str]:
    mem_total = _to_float(node.get("memory_total"))
    mem_used = _to_float(node.get("memory_used"))
    mem_free = max(mem_total - mem_used, 0.0)

    cpu_total = _to_float(node.get("cpu_total"), 1.0)
    cpu_used = _to_float(node.get("cpu_used"), 0.0)
    cpu_ratio = cpu_used / cpu_total if cpu_total > 0 else 1.0

    # Sort key: more free memory, lower cpu ratio, fewer running vms, deterministic node name
    return (-mem_free, cpu_ratio, running_vm_count, str(node.get("node_name") or ""))


def choose_cluster_node(
    nodes: list[dict[str, Any]],
    running_counts_by_node: dict[str, int],
    placement_policy: str,
    default_node: str | None,
    allowed_nodes: set[str] | None = None,
) -> PlacementDecision:
    policy = (placement_policy or "").strip() or (
        "prefer_default_then_balance" if default_node else "balanced"
    )
    online_nodes = [n for n in nodes if _is_online(n)]
    if allowed_nodes is not None:
        online_nodes = [
            n for n in online_nodes if (n.get("node_name") in allowed_nodes)
        ]

    if not online_nodes:
        raise PlacementError("No online Proxmox nodes are available for placement.")

    online_names = {n.get("node_name") for n in online_nodes}

    if policy == "manual":
        if not default_node:
            raise PlacementError(
                "Placement policy manual requires a configured default node."
            )
        if default_node not in online_names:
            raise PlacementError(
                f"Placement policy manual selected {default_node}, but that node is offline or unavailable."
            )
        return PlacementDecision(
            default_node, "manual default node", {"policy": policy}
        )

    if (
        policy == "prefer_default_then_balance"
        and default_node
        and default_node in online_names
    ):
        return PlacementDecision(
            default_node, "preferred default node is online", {"policy": policy}
        )

    scored = sorted(
        online_nodes,
        key=lambda n: _score(
            n, running_counts_by_node.get(n.get("node_name") or "", 0)
        ),
    )
    selected = scored[0]
    return PlacementDecision(
        selected_node=selected.get("node_name") or "",
        reason="balanced selection based on memory/cpu/running-vm load",
        details={
            "policy": policy,
            "candidate_count": len(scored),
        },
    )
