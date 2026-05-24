# Cluster-aware placement and asset readiness

This platform performs **cluster-aware placement** for VM creation using active Proxmox cluster metadata.

## Eligibility checks
A node is eligible only when:
- node is online,
- selected template is available (or supported clone path is known),
- selected/default storage is available,
- selected/default bridge is available.

## Placement policy
- `manual`: only default node
- `balanced`: score eligible nodes by free memory, CPU usage, running VM count, then node name
- `prefer_default_then_balance`: use default if eligible, else balance

## Readiness and sync
Use:
- `GET /api/admin/proxmox/clusters/{id}/readiness`
- `GET /api/admin/proxmox/templates/availability`
- `GET /api/admin/proxmox/clusters/{id}/isos`
- `GET /api/admin/proxmox/assets/readiness`

Asset sync endpoints are explicit admin actions and currently return dry-run/unsupported guidance in cloud-safe mode.
Never assume template VMIDs can be duplicated blindly across nodes.
