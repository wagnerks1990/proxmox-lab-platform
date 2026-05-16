# Development Workflow

## Branch model
- `main`: stable production
- `develop`: integration testing
- `feature/*`: scoped implementation

## Backend refactor policy
- Keep API paths backward-compatible during route splitting.
- Move logic from `routes_legacy.py` into modular route files incrementally.
- Use service-layer modules to avoid route bloat.

## Proxmox-only scope
- Classroom VDI orchestration on Proxmox clusters/nodes only.
- No multi-hypervisor abstraction in this project.

## Schema drift policy
- Prefer tolerant Alembic migrations for existing drifted databases.
- Never drop data as part of Codex migration fixes.

## Safe testing policy
- Allowed in Codex:
  - `python3 -m compileall backend/app`
  - `cd frontend && npm run build`
- Disallowed in Codex:
  - destructive Proxmox actions
  - deployment scripts
  - live runtime integration/destructive tests
