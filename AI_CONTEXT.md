# LabGoblin AI contributor context

Read this file, `AGENTS.md`, `docs/brand.md`, and the documentation page for the feature before changing code.

## Canonical identity

- Product: **LabGoblin**
- Category: **Virtual Lab Provisioning & Management**
- Primary tagline: **Real Skills. Virtual Machines.**
- Campaign line: **Build. Deploy. Learn. Repeat.**
- Legacy identity: `Proxmox Lab Platform` / `proxmox-lab-platform`

All new user-facing text must use **LabGoblin**. Proxmox VE is an infrastructure integration, not part of the product name.

## Product boundary

LabGoblin is a classroom control plane. PostgreSQL is authoritative for desired state; Proxmox VE is an external system whose observed state must be reconciled. Students never gain broad Proxmox access.

## Branding migration rules

- Change display names, UI copy, docs headings, browser metadata, API titles, screenshots, and help text to LabGoblin.
- Preserve legacy deployment paths, updater service/group names, database identifiers, environment variable names, and API identifiers until a compatibility-safe migration exists.
- Do not break installed systems solely to achieve cosmetic renaming.
- If a compatibility-sensitive legacy identifier is replaced, add migration/alias handling and document rollback impact.
- Keep README, source-controlled wiki, operator docs, release notes, and AI-aware files synchronized.
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

Run backend tests, frontend tests/build, dependency audits, the single-head migration check, strict documentation build, and generated-contract drift check. Offline tests do not prove behavior against a real Proxmox cluster.

## Useful entry points

- API composition: `backend/app/api/routes.py`
- Authorization: `backend/app/api/deps.py`, `backend/app/services/organization_access.py`
- Durable work: `backend/app/services/operation_service.py`, `backend/app/workers/operation_worker.py`
- Proxmox adapter: `backend/app/services/proxmox.py`
- Classroom policy: `backend/app/services/classroom_access.py`
- Deployment: `deploy/install.sh`, `deploy/updater_agent.py`, `docker-compose.yml`
- Contract: `frontend/openapi.json`, `frontend/src/generated/api-schema.d.ts`
- Brand: `docs/brand.md`, `frontend/public/brand/`
