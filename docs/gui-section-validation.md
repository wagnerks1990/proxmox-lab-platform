# GUI Section Validation (Current Proxmox-Connected Configuration)

Recommended order:
1. Login with `admin / admin`.
2. Open **Proxmox Setup** and validate active cluster discovery (nodes/storage/templates/networks).
3. Open **Proxmox Inventory** and run **Sync all templates**.
4. Open **Create VM** and verify templates are available.
5. Validate **My Lab VMs**, **Sessions**, **Pools**, **Telemetry**, **Operations**, and **Troubleshooting** empty/error states.

Notes:
- Raw Proxmox inventory (node/vmid scoped) is separate from app-managed lab VMs (`student_vms.id`).
- Templates must be imported/synced into app `vm_templates` before Create VM can provision lab VMs.
- Placement/load-balancing behavior depends on template and storage availability across nodes.
