# LabGoblin

**Virtual Lab Provisioning & Management**  
**Real Skills. Virtual Machines.**

LabGoblin is a classroom-focused control plane for giving students controlled access to virtual lab resources while instructors manage templates, assignments, scheduling, provisioning, lifecycle operations, and auditability.

> **Development status:** the current application is an alpha. It is suitable for isolated development and review, but it is not yet approved for unsupervised student or production use. The V2 stabilization and rebuild roadmap is documented in [`docs/roadmap/v2-rebuild.md`](docs/roadmap/v2-rebuild.md).

The source-controlled documentation wiki starts at [`docs/index.md`](docs/index.md). Brand and naming rules are documented in [`docs/brand.md`](docs/brand.md).

## Brand identity

- **Product:** LabGoblin
- **Category:** Virtual Lab Provisioning & Management
- **Primary tagline:** Real Skills. Virtual Machines.
- **Campaign line:** Build. Deploy. Learn. Repeat.
- **Primary color:** Goblin Green `#22C55E`
- **Primary dark:** Deep Space `#0B1220`

LabGoblin is the product identity. **Proxmox VE** is currently the underlying hypervisor integration and is referenced by name only where technically relevant.

## Appliance installation

A dedicated Debian or Ubuntu VM on the Proxmox cluster is the recommended deployment target. The GitHub repository itself has not yet been renamed, so the working installation URL is currently:

```bash
curl -fsSL https://raw.githubusercontent.com/wagnerks1990/proxmox-lab-platform/main/deploy/install.sh | sudo sh
```

The repository URL above is only an upstream locator. A fresh installation is fully LabGoblin-native: `/opt/labgoblin`, `/var/lib/labgoblin`, the `labgoblin-updater` service/group, LabGoblin database defaults, and LabGoblin application identifiers.

The installer deploys LabGoblin with Docker Compose, generates bootstrap secrets, runs database migrations, installs the local update agent, and waits for the application health gate. See [`docs/operations/deployment.md`](docs/operations/deployment.md) before using the direct-on-hypervisor override. For a private repository, clone with a read-only deploy key first; unauthenticated `raw.githubusercontent.com` links do not work for private repositories.

## Stack
- Frontend: React + Vite
- Backend: FastAPI + SQLAlchemy
- DB: PostgreSQL
- Auth: revocable JWT sessions in HttpOnly same-site cookies + bcrypt password hashing

## Project structure
- `backend/app/main.py` – FastAPI entrypoint
- `backend/app/api/routes.py` – REST endpoints
- `backend/app/models/models.py` – relational models (`users`, `roles`, `vm_templates`, `student_vms`, `permissions`, `audit_logs`)
- `backend/app/services/proxmox.py` – secure backend-only Proxmox API client
- `backend/init.sql` – seed data
- `frontend/src/main.jsx` – application routes and bootstrap
- `frontend/public/brand/` – application branding assets

## Working development features

- organization membership and tenant roles;
- revocable login sessions, password lifecycle, and persistent login throttling;
- instructor-scoped classes, rosters, lab blueprints, scheduled runs, and assignments;
- student VM access gated by membership, enrollment, assignment, run window, and ownership;
- template discovery/import, placement-aware VM provisioning, lifecycle controls, and reconciliation;
- Docker Compose installation, health-gated GitHub updates, and rollback;
- structured identity and classroom audit events;
- source-controlled MkDocs wiki and CI validation.

The current API is mounted at `/api` and `/v1/api` during the versioned transition. Interactive OpenAPI documentation is available at `/docs` on a running development installation and is branded as the **LabGoblin API**.

## Disposable live test

The repository includes a stateful Proxmox simulator and a guarded end-to-end test. It exercises first-admin enrollment, organization and classroom setup, student authorization, durable VM clone/start/stop/delete operations, and logout through the public HTTP API. The test is destructive and is intended only for the disposable Docker Compose database created for CI.

```bash
export POSTGRES_PASSWORD='live-test-database-password'
export JWT_SECRET_KEY='live-test-jwt-secret-at-least-32-characters'
export CONFIG_ENCRYPTION_KEY='live-test-encryption-key-at-least-32-characters'
export UPDATER_TOKEN='live-test-updater-token'
export BOOTSTRAP_ADMIN_TOKEN='live-test-bootstrap-token'
export UPDATER_GID='0'
docker compose -f docker-compose.yml -f docker-compose.live-test.yml up -d --build
python scripts/live_test.py --bootstrap-token "$BOOTSTRAP_ADMIN_TOKEN" \
  --i-understand-this-deletes-data
docker compose -f docker-compose.yml -f docker-compose.live-test.yml down \
  --volumes --remove-orphans
```

See [`docs/operations/live-test.md`](docs/operations/live-test.md) for safety boundaries, troubleshooting, and what this simulator does not prove.

## Development setup

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/ensure_config_encryption_key.py --create
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## First administrator

A fresh appliance has no default password. The installer prints a random, one-time bootstrap token used by the first-run page to create the initial administrator. See [`docs/operations/first-run.md`](docs/operations/first-run.md).

## Proxmox VE configuration

Set the appropriate configuration in `backend/.env` or configure the integration through the administration interface. Relevant variables include:

- `PROXMOX_BASE_URL`
- `PROXMOX_TOKEN_ID`
- `PROXMOX_TOKEN_SECRET`
- `PROXMOX_VERIFY_SSL`

The token is used only by the backend service and is never exposed to frontend code. LabGoblin-generated Proxmox tokens default to the token ID `labgoblin`.

## LabGoblin runtime identifiers

Fresh installations use these canonical application-owned names:

- install root: `/opt/labgoblin`
- state root: `/var/lib/labgoblin`
- Compose project: `labgoblin`
- default PostgreSQL database/user: `labgoblin`
- web session cookie: `labgoblin_session`
- updater unit/group: `labgoblin-updater.service` / `labgoblin-updater`
- updater executable: `/usr/local/lib/labgoblin-updater.py`
- host runner: `labgoblin-runner`
- frontend package: `labgoblin-frontend`

Proxmox-specific names remain where they describe the actual hypervisor integration rather than LabGoblin itself.

## Security notes

- Passwords are stored as bcrypt hashes.
- VM actions require authenticated authorization.
- Student provisioning requires an active classroom assignment; legacy direct and group template permissions are not sufficient.
- VM operations are auditable.
- Secret values are sourced from protected configuration.
- Branding changes must never weaken authorization, tenant isolation, updater safety, or audit behavior.

## Post-pull validation

Run this command to validate current live backend health after pulling changes:

```bash
python backend/scripts/validate_deploy.py
```

It checks backend module compilation, required architecture events, a single Alembic head, database connectivity, and live `/api/health` state.

## SSE proxy requirement

For `/api/admin/events/stream` (EventSource/SSE), include the dedicated NGINX location block from `deploy/nginx/sse-events-stream.conf`. This disables proxy buffering and keeps the stream open so live telemetry can remain connected.

## Naming policy

This repository is development software intended for fresh installation, so LabGoblin-owned technical identifiers do not preserve predecessor names. The sole temporary exception is the current GitHub repository slug, which remains in working repository/install/update URLs until the repository itself is renamed. See [`docs/brand.md`](docs/brand.md).

## Future expansion-ready

The architecture leaves space for quotas, scheduled cleanup, snapshots, VLAN/private network workflows, SSO providers, embedded remote consoles, and broader hypervisor abstraction.
