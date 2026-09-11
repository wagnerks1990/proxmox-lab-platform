# Codex Cloud Workflow for LabGoblin

## A. Purpose
This document defines what Codex Cloud can safely do for the LabGoblin repository and what must still be validated manually on the Ubuntu deployment server.

Codex and other coding agents must also follow `AGENTS.md`, `AI_CONTEXT.md`, and `docs/brand.md`.

## B. What Codex Cloud can do
- repository inspection
- documentation updates
- guarded source code changes
- frontend build checks when dependencies are available
- backend compile checks when dependencies are available
- focused tests
- PR creation
- code review
- migration structure inspection

## C. What Codex Cloud must not claim to validate
- nginx live config
- systemd restart behavior
- production PostgreSQL state
- production Alembic current revision
- live Proxmox VE API behavior
- live SSE browser behavior
- live Guacamole behavior
- live ttyd behavior
- production browser login
- actual VM lifecycle behavior on the Proxmox cluster

## D. Required pre-edit check
Run:

```bash
git status --short
```

If the working tree is not clean, Codex should stop and report dirty files before making changes.

## E. Recommended Cloud checks
These may require dependencies to already exist in the environment.

Backend:

```bash
cd backend
python -m compileall app tests
```

Alembic structure:

```bash
cd backend
alembic heads
alembic history | tail -n 30
```

Frontend:

```bash
cd frontend
npm ci
npm test
npm run build
```

Cloud-safe validation script:

```bash
./scripts/codex_cloud_check.sh
```

Branding/repository validation:

```bash
python scripts/check_branding.py
```

## F. Dependency note
If the environment setup is minimal and dependencies are not installed, Codex must not fake build/test success. It should report that dependency-backed checks were not run and explain why.

## G. Manual Ubuntu server validation checklist

Fresh LabGoblin installations use `/opt/labgoblin` and LabGoblin-prefixed services and helpers.

```bash
cd /opt/labgoblin/app
git pull

cd backend
source venv/bin/activate
alembic heads
alembic upgrade heads
python scripts/validate_deploy.py

cd ../frontend
npm ci
npm test
npm run build

sudo nginx -t
sudo systemctl restart labgoblin-updater.service
curl http://127.0.0.1:8080/api/ready
```

## H. Manual browser validation checklist
- LabGoblin branding appears on login and application shell
- login works
- `/api/auth/me` works
- Dashboard loads
- VMs page loads
- VM list loads
- VM create still works
- VM start/stop/reboot/delete still work
- Templates page loads
- Pools page loads
- Operations page loads
- Troubleshooting page loads
- Telemetry page loads
- Session Activity page loads
- SSE stream connects
- Web Terminal behavior is clear and not fake
- unsupported protocol buttons are hidden or disabled

## I. Branding validation
A branding pass must distinguish LabGoblin-owned names from legitimate Proxmox VE integration terms. It must reject retired application-owned runtime/repository names such as `proxmox_lab`, `plp_session`, `/opt/proxmox-lab-platform`, `/var/lib/proxmox-lab-platform`, `proxmox-lab-*`, and `wagnerks1990/proxmox-lab-platform`. The canonical repository is `wagnerks1990/labgoblin`.

## J. PR expectations
Every Codex Cloud PR must include:
- summary of changes
- backend changes
- frontend changes
- documentation/branding changes
- migration changes
- tests/checks run
- tests/checks not run and why
- what still requires Ubuntu server validation
- known risks
- intentionally deferred items
