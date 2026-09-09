# Proxmox Lab Access Platform

Classroom-focused control plane for managing student access to Proxmox lab
resources.

> **Development status:** the current application is an alpha. It is suitable
> for isolated development and review, but it is not yet approved for
> unsupervised student or production use. The V2 stabilization and rebuild
> roadmap is documented in [`docs/roadmap/v2-rebuild.md`](docs/roadmap/v2-rebuild.md).

The source-controlled documentation wiki starts at [`docs/index.md`](docs/index.md).

## Appliance installation

A dedicated Debian or Ubuntu VM on the Proxmox cluster is the recommended
deployment target. When the repository is public, installation is one command:

```bash
curl -fsSL https://raw.githubusercontent.com/wagnerks1990/proxmox-lab-platform/main/deploy/install.sh | sudo sh
```

The installer deploys the application with Docker Compose, generates bootstrap
secrets, runs database migrations, installs the local update agent, and waits
for the application health gate. See
[`docs/operations/deployment.md`](docs/operations/deployment.md) before using
the direct-on-hypervisor override. For a private repository, clone with a
read-only deploy key first; unauthenticated `raw.githubusercontent.com` links do
not work for private repositories.

## Stack
- Frontend: React + Vite (Tailwind-ready)
- Backend: FastAPI + SQLAlchemy
- DB: PostgreSQL
- Auth: revocable JWT sessions in HttpOnly same-site cookies + bcrypt password hashing

## Project structure
- `backend/app/main.py` – FastAPI entrypoint
- `backend/app/api/routes.py` – REST endpoints
- `backend/app/models/models.py` – relational models (`users`, `roles`, `vm_templates`, `student_vms`, `permissions`, `audit_logs`)
- `backend/app/services/proxmox.py` – secure backend-only Proxmox API client
- `backend/init.sql` – seed data
- `frontend/src/main.jsx` – login + role dashboard + template list + VM create UI

## Working development features

- organization membership and tenant roles;
- revocable login sessions, password lifecycle, and persistent login throttling;
- instructor-scoped classes, rosters, lab blueprints, scheduled runs, and assignments;
- student VM access gated by membership, enrollment, assignment, run window, and ownership;
- template discovery/import, placement-aware VM provisioning, lifecycle controls, and reconciliation;
- Docker Compose installation, health-gated GitHub updates, and rollback;
- structured identity and classroom audit events;
- source-controlled MkDocs wiki and CI validation.

The current API is mounted at `/api` and `/v1/api` during the versioned
transition. Interactive OpenAPI documentation is available at `/docs` on a
running development installation.

## Disposable live test

The repository includes a stateful Proxmox simulator and a guarded end-to-end
test. It exercises first-admin enrollment, organization and classroom setup,
student authorization, durable VM clone/start/stop/delete operations, and
logout through the public HTTP API. The test is destructive and is intended
only for the disposable Docker Compose database created for CI.

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

See [`docs/operations/live-test.md`](docs/operations/live-test.md) for safety
boundaries, troubleshooting, and what this simulator does not prove.

## Setup
1. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Generate and review secrets before continuing.
python scripts/ensure_config_encryption_key.py --create
alembic upgrade head
uvicorn app.main:app --reload
```

2. Frontend
```bash
cd frontend
npm install
npm run dev
```

## First administrator

A fresh appliance has no default password. The installer prints a random,
one-time bootstrap token used by the first-run page to create the initial
administrator. See [`docs/operations/first-run.md`](docs/operations/first-run.md).

## Proxmox configuration
Set in `backend/.env`:
- `PROXMOX_BASE_URL`
- `PROXMOX_TOKEN_ID`
- `PROXMOX_TOKEN_SECRET`
- `PROXMOX_VERIFY_SSL`

The token is used only by backend service (`app/services/proxmox.py`) and never exposed to frontend.

## Security notes
- Passwords stored as bcrypt hashes.
- All VM actions require JWT auth.
- Student provisioning requires an active classroom assignment; legacy direct
  and group template permissions are not sufficient.
- VM create action logs to `audit_logs`.
- Secret values sourced from environment variables.

## Post-pull validation (recommended)
Run this single command to validate current live backend health after pulling changes:

```bash
python backend/scripts/validate_deploy.py
```

It checks:
- backend app modules compile
- `SESSION_EXPIRED` exists in `app.architecture.events`
- Alembic reports exactly one head
- database connectivity (`SELECT 1`)
- live `/api/health` response is fully OK (`backend`, `database`, `proxmox`)

This command validates the *current* deployment state and does not treat stale historical journal entries from older restarts as active failures.

## SSE proxy requirement (production)
For `/api/admin/events/stream` (EventSource/SSE), include the dedicated NGINX location block from:

- `deploy/nginx/sse-events-stream.conf`

This disables proxy buffering and keeps the stream open so live telemetry status transitions to connected in the GUI.

## Future expansion-ready
Architecture leaves space for:
- class/group and quota tables
- scheduled cleanup jobs
- snapshots
- VLAN/private network workflows
- SSO providers
- embedded noVNC
