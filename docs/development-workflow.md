# Development Workflow

## Branch model
- `main`: source of truth for the current alpha and release candidates
- `feature/*`, `fix/*`, and `audit/*`: scoped branches created from `main`

There is no active `develop` branch. Merging to `main` does not by itself confer
production support; the pre-production acceptance gates remain authoritative.

## Backend refactor policy
- Keep API paths backward-compatible during route splitting.
- Keep route logic in feature routers under `backend/app/api/routers`; the legacy router has been removed.
- Use service-layer modules to avoid route bloat.

## Proxmox-only scope
- Classroom VDI orchestration on Proxmox clusters/nodes only.
- No multi-hypervisor abstraction in this project.

## Schema drift policy
- Prefer tolerant Alembic migrations for existing drifted databases.
- Never drop data as part of Codex migration fixes.

## Safe testing policy
- Safe local and disposable validation is expected when its dependencies are
  available. Use `docs/development/validation.md` for the canonical commands.
- The disposable Compose live test may run only against its isolated local
  database and simulator with the required destructive-test acknowledgement.
- Never run destructive actions against a real Proxmox cluster, a reused
  database, or an actual deployment from an unattended development environment.
- Real-cluster, browser-console, TLS, update-recovery, and restore tests belong
  to the isolated acceptance environment and must be recorded in the
  pre-production acceptance checklist.
