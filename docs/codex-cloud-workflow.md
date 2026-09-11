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

If the working tree is not clean, Codex must identify and preserve unrelated
changes. It may continue only when its work can be isolated safely; otherwise it
must stop and report the conflict.

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

This is a strict gate covering required repository files, branding and repository
hygiene, shell and Compose syntax, backend formatting/lint/tests/security audits,
frontend tests/build/audit, generated-contract drift, and the strict documentation
build. A missing tool or dependency is a failed gate with setup guidance, not a
skipped success.

Branding/repository validation:

```bash
python scripts/check_branding.py
```

## F. Dependency note
If the environment setup is minimal and dependencies are not installed, the
validation script exits nonzero and prints setup guidance. Codex must report that
failure and must not describe the gate as passed.

## G. Ubuntu appliance validation checklist

Fresh LabGoblin installations use `/opt/labgoblin` and LabGoblin-prefixed services and helpers.

```bash
cd /opt/labgoblin/app
sudo systemctl status labgoblin-updater.service --no-pager
sudo docker compose --env-file .env ps
sudo docker compose --env-file .env exec -T api alembic current
sudo docker compose --env-file .env exec -T api alembic heads
sudo docker compose --env-file .env exec -T api python scripts/validate_deploy.py
curl -fsS http://127.0.0.1:8080/api/ready
```

Use the administrator update workflow for deployed upgrades. Do not bypass its
backup, exact-commit, health, and rollback controls with `git pull`, a host
virtualenv, or a manual frontend build. Complete and retain the evidence listed
in [Pre-production acceptance](operations/preproduction-acceptance.md).

## H. Manual browser validation checklist

Record browser, viewport, commit, role, environment, and result. Use the full
[GUI validation matrix](gui-section-validation.md); at minimum confirm:

- LabGoblin branding appears on login and the application shell.
- Login, bootstrap, forced password change, logout, and unavailable states are
  distinct and announced.
- The skip link, active destination, desktop collapse, compact drawer, bottom
  navigation, and organization switcher work by keyboard.
- Student, instructor, tenant-admin/owner, and platform-admin navigation matches
  capabilities, including direct access to forbidden URLs.
- Dashboard, Lab VMs, Create VM, Classroom, Pools, Sessions, Events, Operations,
  Telemetry, Troubleshooting, Proxmox Setup, Inventory, Assets, Templates, Users,
  Groups, Organizations, Updates, and Account Security show honest loading,
  empty, error, and populated states.
- VM create/start/stop/reboot/delete remains durable and never displays queued
  work as completed external state.
- SSE connects through the deployed proxy and terminates after revocation.
- noVNC resizes and handles reconnect, expiry, and revocation.
- SSH terminal is hidden or denied unless its security prerequisites are enabled
  and validated.
- Unsupported protocol buttons are hidden or clearly unavailable.
- The interface passes at 320, 390, 768, 1024, and 1440 CSS pixel widths, 200%
  zoom, and keyboard-only navigation.

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
- role, viewport, accessibility, and view-state evidence for changed workflows
- what still requires Ubuntu server validation
- known risks
- intentionally deferred items
