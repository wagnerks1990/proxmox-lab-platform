# Development database reset to canonical baseline

## Why this reset exists
The development Alembic history drifted into multiple heads and conflicting schema operations (including duplicate `console_enabled` additions on `student_vms`). This reset replaces that broken history with one canonical development baseline migration (`20260521_0001`).

## Warning
This process **destroys development app database data**. Back up first if you need to preserve development records.

## Ubuntu commands
```bash
cd /opt/proxmox-lab-platform
git pull

cd backend
source venv/bin/activate

pg_dump proxmox_lab > /root/proxmox_lab_before_dev_reset_$(date +%F_%H%M%S).sql

RESET_DEV_DB_CONFIRM=YES ./scripts/reset_dev_database.sh

export DEV_ADMIN_USERNAME=Kyle
export DEV_ADMIN_EMAIL=<your-admin-email>
export DEV_ADMIN_PASSWORD=<temporary-password>
python scripts/seed_dev_admin.py

python -m compileall app
alembic heads
alembic current
python scripts/validate_deploy.py

cd ../frontend
npm install
npm run build

sudo nginx -t
sudo systemctl restart proxmox-lab-backend
sleep 3
curl -sS http://127.0.0.1:8000/api/health
```

## Expected result
- `alembic heads` shows `20260521_0001`
- `alembic current` shows `20260521_0001`
- `python scripts/validate_deploy.py` passes
- `http://127.0.0.1:8000/api/health` responds successfully

## Backup note
Use `pg_dump` before reset if any development data might need recovery.

## Scope note
This reset affects **application database records only**. It does not delete or modify Proxmox VM assets directly.
