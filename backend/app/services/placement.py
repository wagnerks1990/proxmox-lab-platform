from app.models.models import ProxmoxNode, StudentVM, VMPool


def select_node_for_pool(db, pool: VMPool):
    strategy = (pool.placement_strategy or 'any_enabled_node').lower()
    nodes_q = db.query(ProxmoxNode).filter(ProxmoxNode.enabled.is_(True))
    if pool.cluster_id:
        nodes_q = nodes_q.filter(ProxmoxNode.cluster_id == pool.cluster_id)
    nodes = nodes_q.all()
    if not nodes:
        return None
    if strategy == 'fixed_node' and pool.preferred_node_id:
        return db.query(ProxmoxNode).filter(ProxmoxNode.id == pool.preferred_node_id, ProxmoxNode.enabled.is_(True)).first()
    if strategy == 'least_running_vms':
        return min(nodes, key=lambda n: db.query(StudentVM).filter(StudentVM.proxmox_node == n.node_name, StudentVM.status == 'running').count())
    if strategy == 'least_memory_usage':
        return sorted(nodes, key=lambda n: float((n.memory_usage or '0').split('%')[0] or 0))[0]
    if strategy == 'round_robin':
        return nodes[db.query(StudentVM).count() % len(nodes)]
    return nodes[0]
