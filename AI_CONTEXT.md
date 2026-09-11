# LabGoblin AI contributor context

Read this file, `AGENTS.md`, `docs/brand.md`, and the documentation page for the feature before changing code.

## Canonical identity

- Product: **LabGoblin**
- Category: **Virtual Lab Provisioning & Management**
- Primary tagline: **Real Skills. Virtual Machines.**
- Campaign line: **Build. Deploy. Learn. Repeat.**
- Canonical technical identifier: `labgoblin`
- Canonical service prefix: `labgoblin-`
- Install root: `/opt/labgoblin`
- State root: `/var/lib/labgoblin`
- Session cookie: `labgoblin_session`

All user-facing and LabGoblin-owned technical identifiers must use LabGoblin naming. Proxmox VE is an infrastructure integration, not part of the product name.

## Product boundary

LabGoblin is a classroom control plane. PostgreSQL is authoritative for desired state; Proxmox VE is an external system whose observed state must be reconciled. Students never gain broad Proxmox access.

## Clean-install branding rules

This repository is development software intended for fresh installation. There is no requirement to preserve predecessor installation paths, service names, database defaults, package names, cookie names, logger namespaces, helper names, or updater state paths.

- Do not introduce new LabGoblin-owned identifiers using `proxmox-lab-platform`, `proxmox_lab`, `plp_`, or `proxmox-lab-*` naming.
- Keep `PROXMOX_*`, `ProxmoxCluster`, Proxmox API routes/fields, and similar terminology when they genuinely describe the Proxmox VE integration.
- The current GitHub repository URL may still contain the predecessor slug until the repository itself is renamed. Treat that URL only as an upstream locator, not as canonical product naming.
- Keep README, source-controlled wiki, operator docs, release notes, frontend metadata, deployment code, tests, and AI-aware files synchronized.
- Do not imply that LabGoblin is affiliated with, endorsed by, or part of Proxmox Server Solutions GmbH.

## Design tokens

- Goblin Green: `#22C55E`
- Deep Space: `#0B1220`
- Slate Surface: `#1F2937`
- Steel Secondary: `#3B4754`
- Cloud Light: `#E5E7EB`
- Mint Accent: `#A7F3D0`
- UI/body type: Inter or system-ui fallback

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

Run backend tests, frontend tests/build, dependency audits, the single-head migration check, strict documentation build, generated-contract drift check, and branding regression checks. Offline tests do not prove behavior against a real Proxmox cluster.

## Useful entry points

- API composition: `backend/app/api/routes.py`
- Authorization: `backend/app/api/deps.py`, `backend/app/services/organization_access.py`
- Durable work: `backend/app/services/operation_service.py`, `backend/app/workers/operation_worker.py`
- Proxmox adapter: `backend/app/services/proxmox.py`
- Classroom policy: `backend/app/services/classroom_access.py`
- Deployment: `deploy/install.sh`, `deploy/updater_agent.py`, `deploy/labgoblin-updater.service`, `docker-compose.yml`
- Contract: `frontend/openapi.json`, `frontend/src/generated/api-schema.d.ts`
- Brand: `docs/brand.md`, `frontend/public/brand/`
