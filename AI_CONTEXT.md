# AI contributor context

Read this file, `AGENTS.md`, and the documentation page for the feature before changing code.

## Product boundary

Proxmox Lab Platform is a classroom control plane. PostgreSQL is authoritative for desired state; Proxmox is an external system whose observed state must be reconciled. Students never gain broad Proxmox access.

## Non-negotiable invariants

- Resolve organization membership and object ownership on every request.
- Persist Proxmox mutations as `durable_operations` before calling Proxmox.
- Store the Proxmox UPID, use idempotency keys, lease jobs, and verify results.
- Allocate VMIDs through `vmid_allocators`; never calculate them from row counts.
- Preview destructive actions and require an explicit confirmation value.
- Keep JWTs in HttpOnly cookies. Never put JWTs, tickets, credentials, keys, or provider secrets in URLs, logs, browser storage, or normal API responses.
- Treat AI-generated material as untrusted advice. AI is read-only until a human approves a normal, authorized durable operation.
- Add a linear Alembic migration for schema changes and regenerate the OpenAPI contract.

## Validation

Run backend tests, frontend tests/build, dependency audits, the single-head migration check, strict documentation build, and generated-contract drift check. Offline tests do not prove behavior against a real Proxmox cluster.

## Useful entry points

- API composition: `backend/app/api/routes.py`
- Authorization: `backend/app/api/deps.py`, `backend/app/services/organization_access.py`
- Durable work: `backend/app/services/operation_service.py`, `backend/app/workers/operation_worker.py`
- Proxmox adapter: `backend/app/services/proxmox.py`
- Classroom policy: `backend/app/services/classroom_access.py`
- Deployment: `deploy/install.sh`, `deploy/updater_agent.py`, `docker-compose.yml`
- Contract: `frontend/openapi.json`, `frontend/src/generated/api-schema.d.ts`
