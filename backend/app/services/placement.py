
def get_eligible_nodes(nodes, strategy='any_enabled_node'):
    eligible = [n for n in nodes if n.get('enabled', True) and n.get('status') in [None, 'online', 'up']]
    return eligible


def explain_ineligible_nodes(nodes):
    out = []
    for n in nodes:
        reasons = []
        if not n.get('enabled', True):
            reasons.append('node disabled for placement')
        if n.get('status') not in [None, 'online', 'up']:
            reasons.append('node not online')
        if reasons:
            out.append({'node': n.get('node_name') or n.get('node'), 'reasons': reasons})
    return out


def choose_node(strategy, eligible_nodes):
    if not eligible_nodes:
        return None
    if strategy == 'least_running_vms':
        return sorted(eligible_nodes, key=lambda n: n.get('running_vm_count', 0))[0]
    if strategy == 'least_memory_usage':
        return sorted(eligible_nodes, key=lambda n: float(str(n.get('memory_usage', '0')).replace('%', '') or 0))[0]
    if strategy == 'least_cpu_usage':
        return sorted(eligible_nodes, key=lambda n: float(str(n.get('cpu_usage', '0')).replace('%', '') or 0))[0]
    return eligible_nodes[0]


def validate_placement_request(nodes, strategy='any_enabled_node'):
    eligible = get_eligible_nodes(nodes, strategy)
    return {'strategy': strategy, 'eligible_nodes': eligible, 'ineligible_nodes': explain_ineligible_nodes(nodes), 'chosen_node': choose_node(strategy, eligible)}
