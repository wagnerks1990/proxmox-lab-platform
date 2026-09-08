# Backend architecture

The FastAPI application is Proxmox-only. `app/api/routes.py` composes feature
routers from `app/api/routers/`; there is no legacy parallel router.

## Request boundary

Authentication accepts a bearer token for API tooling or the HttpOnly
`plp_session` cookie used by the web application. The token must map to a live
`auth_sessions` record and the current user token version. Organization context
is resolved independently and fails closed for unknown roles or inactive
memberships.

Routers validate policy and create desired state. They do not own long-running
Proxmox mutations. VM mutation routes commit `durable_operations` and return
HTTP `202` with an operation identifier.

## Service boundary

- `services/proxmox.py` is the backend-only Proxmox adapter.
- `services/operation_service.py` allocates VMIDs, queues, leases, executes,
  retries, and verifies infrastructure operations.
- `services/classroom_access.py` evaluates enrollment, assignment, schedule,
  ownership, and lab access flags.
- `services/organization_access.py` resolves tenant scope and role rank.
- `services/asset_sync.py` manages restart-safe asset jobs with JSON metadata.
- `services/console_ws_service.py` brokers noVNC and key-based SSH without
  disclosing control-plane credentials.

## Background work

APScheduler currently runs inside the API process. Durable operations use
PostgreSQL row leases, while worker overlap and reconnect-token replay use
Redis in Compose. Asset jobs are claimed from PostgreSQL. This is safe for the
single-API pilot; separating worker and scheduler processes remains required
before horizontal API scaling.

## Persistence and contracts

SQLAlchemy models live in `app/models/models.py`; all schema changes use the
single linear Alembic history. OpenAPI is exported to `frontend/openapi.json`
and produces `frontend/src/generated/api-schema.d.ts`. CI rejects contract
drift.

## Remote access

The current supported browser paths are same-origin noVNC and SSH WebSockets.
RDP downloads a credential-prompting file. SPICE remains a native-client path.
Guacamole is the longer-term broker but is not part of the current Compose
deployment.
