# Route Cutover Plan

## Legacy handlers found in `app/api/routes.py`

- auth: `/auth/login`, `/auth/me` -> `routers/auth.py` (duplicate, remove legacy)
- health: `/health` -> `routers/health.py` (duplicate, remove legacy)
- templates: `/templates`, `/admin/templates*` -> `routers/templates.py` (duplicate, remove legacy)
- audit: `/admin/audit-logs` -> `routers/audit.py` (duplicate, remove legacy)
- VMs: `/vms*` CRUD/status/network -> `routers/vms.py` (partial duplicate; move network/status parity in vms router)
- console/session/websocket/admin ops already in dedicated routers.

## Decision

- Keep `routes.py` as include-only composition.
- Preserve path compatibility through included routers.
- Remove orchestration and direct DB/Proxmox logic from `routes.py`.

## Follow-ups

- complete parity for every legacy VM variant in `routers/vms.py`.
- keep compatibility aliases in dedicated `legacy_compat.py` if needed.
