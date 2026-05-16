# Backend Architecture (Proxmox-only)

This platform is **Proxmox-only** and intentionally does not implement VMware/Hyper-V/XenServer/cloud providers.

## API organization
- `app/api/router.py` central registration.
- Modular route files under `app/api/routes/`:
  - `auth.py`
  - `vms.py`
  - `templates.py`
  - `resource_pools.py`
  - `desktop_pools.py`
  - `proxmox_admin.py`
  - `sessions.py`
  - `monitoring.py`
  - `users.py`
  - `settings.py`
  - `schema_health.py`
- `app/api/routes_legacy.py` currently preserves existing endpoints while logic is incrementally migrated.

## Service layer
- `services/rbac.py`: centralized role normalization + guards.
- `services/placement.py`: placement strategy selection (`fixed_node`, `any_enabled_node`, `least_running_vms`, `least_memory_usage`, `round_robin`).
- `services/schema_health.py`: required table/column checks.
- `services/protocols.py`: protocol registry placeholders (`novnc`, `guacamole`, `rdp`, `spice`, `web_terminal`).

## RBAC strategy
- Source of truth: `users.role_id` -> `roles` table.
- Legacy `users.role` is compatibility-only fallback.

## Safety policy
- No destructive Proxmox operations during Codex runs.
- Safe checks only:
  - `python3 -m compileall backend/app`
  - `cd frontend && npm run build`


## Remote access priority
1. Guacamole (primary browser broker)
2. RDP via Guacamole
3. VNC via Guacamole
4. SSH via Guacamole
5. Direct noVNC/SPICE as future optional fallback placeholders
