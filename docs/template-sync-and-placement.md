# Template Sync and Placement Notes

Load balancing is constrained by real template/storage/bridge availability per Proxmox node.

## Key rules
- A template must be present on candidate nodes for balanced placement to use them.
- If a template exists only on one node, placement will be limited to that node.
- Storage and network bridge availability must also match target node defaults.

## Import vs sync
- **Template import/sync (app DB)** adds/updates `vm_templates` records from discovered Proxmox templates.
- **Template replication across nodes** is a Proxmox-side operation and must be explicit/admin-triggered.

## Current API support
- `GET /api/admin/proxmox/templates/availability`
- `POST /api/admin/proxmox/templates/{vmid}/sync` (validation/dry-run guidance if automated replication is unavailable)

## Recommended setup
1. Configure/validate Proxmox cluster.
2. Import/sync templates into app DB.
3. Replicate templates to all intended nodes using Proxmox-native workflow where required.
4. Confirm availability endpoint reports full node coverage.
5. Use balanced placement.
