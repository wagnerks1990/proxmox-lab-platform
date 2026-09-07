from sqlalchemy import inspect

REQUIRED = {
    'users': ['id', 'username', 'email', 'role_id'],
    'roles': ['id', 'name'],
    'organizations': ['id', 'name', 'slug', 'enabled'],
    'organization_memberships': ['id', 'organization_id', 'user_id', 'role', 'is_active'],
    'student_vms': ['id', 'organization_id', 'owner_id', 'vmid', 'proxmox_node', 'status'],
    'vm_templates': ['id', 'organization_id', 'name', 'proxmox_node', 'source_vmid'],
    'vm_pools': ['id', 'name'],
    'desktop_pools': ['id', 'organization_id', 'name'],
    'connection_launches': ['id', 'actor_id', 'vm_id', 'protocol', 'status', 'created_at'],
    'proxmox_clusters': ['id', 'name', 'api_url'],
    'proxmox_nodes': ['id', 'cluster_id', 'node_name'],
}

def compute_schema_health(bind):
    ins = inspect(bind)
    missing_tables=[]; missing_columns=[]; warnings=[]
    for t, cols in REQUIRED.items():
        if not ins.has_table(t):
            missing_tables.append(t); continue
        existing={c['name'] for c in ins.get_columns(t)}
        for c in cols:
            if c not in existing: missing_columns.append(f'{t}.{c}')
    return {'ok': not missing_tables and not missing_columns, 'missing_tables': missing_tables, 'missing_columns': missing_columns, 'warnings': warnings}
