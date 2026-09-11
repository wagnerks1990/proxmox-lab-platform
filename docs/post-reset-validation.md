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
cd /opt/labgoblin/app/backend
source venv/bin/activate
export PYTHONPATH=/opt/labgoblin/app/backend

python scripts/ensure_config_encryption_key.py

RESET_DEV_USERS_CONFIRM=YES python scripts/reset_dev_users.py

python scripts/validate_post_reset_state.py
python scripts/validate_deploy.py

# Optional development lab seed values
export DEV_TEMPLATE_NAME="Linux Lab Template"
export DEV_ORGANIZATION_SLUG="default"
export DEV_TEMPLATE_VMID="<template-vmid>"
export DEV_TEMPLATE_NODE="<proxmox-node>"
export DEV_TEMPLATE_OS="Linux"
export DEV_RESOURCE_POOL_NAME="Default Resource Pool"
export DEV_DESKTOP_POOL_NAME="Default Desktop Pool"
python scripts/seed_dev_lab_data.py

python scripts/validate_post_reset_state.py
```

Actual Proxmox template VMIDs/nodes must be supplied by an administrator (or set through env vars) when seeding template/pool defaults.
`DEV_ORGANIZATION_SLUG` is required and must identify an enabled organization; seed records are created or updated only inside that organization.

Default development login after reset:
- username: `admin`
- password: `admin`

Warnings:
- `admin/admin` is development-only; never use in production.
- `CONFIG_ENCRYPTION_KEY` is written to the LabGoblin backend environment and must not be committed.
- Back up `CONFIG_ENCRYPTION_KEY`; losing it prevents decrypting stored Proxmox token secrets.
- Do not rotate `CONFIG_ENCRYPTION_KEY` casually after token storage.
