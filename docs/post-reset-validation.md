# Post-reset validation and seed-data workflow

After resetting the development database, run the admin seed and post-reset validation before testing user workflows.

## Scripts

- `python scripts/seed_dev_admin.py` creates/updates Student/Teacher/Admin roles and the specified admin user.
- `python scripts/validate_post_reset_state.py` checks required roles/admin presence and that core tables are queryable.
- `python scripts/seed_dev_lab_data.py` (optional) seeds minimal template/desktop-pool records to make UI flows easier to test.

These scripts **do not call live Proxmox APIs** and **do not create Proxmox VMs**.

## PASS/WARN/FAIL

- `PASS`: check succeeded.
- `WARN`: non-blocking condition (for example, empty templates/pools/VMs or missing optional tables such as `resource_pools` when that table is not required by active routes/services).
- `FAIL`: hard blocker (missing roles, missing active admin, or missing/unqueryable required app tables such as `desktop_pools`).

If `validate_post_reset_state.py` reports a missing **required** table, run the latest migration before re-validating:

```bash
alembic upgrade heads
```

## Ubuntu commands

```bash
cd /opt/proxmox-lab-platform/backend
source venv/bin/activate
set -a
source .env
set +a
export PYTHONPATH=/opt/proxmox-lab-platform/backend

export DEV_ADMIN_USERNAME=Kyle
export DEV_ADMIN_EMAIL="wagnerks1@carlisleschools.org"
export DEV_ADMIN_PASSWORD="<new-password>"
python scripts/seed_dev_admin.py

python scripts/validate_post_reset_state.py

# Optional development lab seed values
export DEV_TEMPLATE_NAME="Linux Lab Template"
export DEV_TEMPLATE_VMID="<template-vmid>"
export DEV_TEMPLATE_NODE="<proxmox-node>"
export DEV_TEMPLATE_OS="Linux"
export DEV_RESOURCE_POOL_NAME="Default Resource Pool"
export DEV_DESKTOP_POOL_NAME="Default Desktop Pool"
python scripts/seed_dev_lab_data.py

python scripts/validate_post_reset_state.py
```

Actual Proxmox template VMIDs/nodes must be supplied by an administrator (or set through env vars) when seeding template/pool defaults.
