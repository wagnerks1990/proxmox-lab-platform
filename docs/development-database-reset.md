# Development database reset to canonical baseline

## Why this reset exists
The development Alembic history drifted into multiple heads and conflicting schema operations (including duplicate `console_enabled` additions on `student_vms`). This reset replaces that broken history with one canonical development baseline migration (`20260521_0001`).

## Warning
This process **destroys development app database data**. Back up first if you need to preserve development records.

## Ubuntu commands
```bash
cd /opt/labgoblin/app
git pull

cd backend
source venv/bin/activate
export PYTHONPATH=/opt/labgoblin/app/backend

python scripts/ensure_config_encryption_key.py

pg_dump labgoblin > /root/labgoblin_before_dev_reset_$(date +%F_%H%M%S).sql

RESET_DEV_DB_CONFIRM=YES ./scripts/reset_dev_database.sh

RESET_DEV_USERS_CONFIRM=YES python scripts/reset_dev_users.py

python -m compileall app
alembic heads
alembic current
python scripts/validate_post_reset_state.py
python scripts/validate_deploy.py

cd ../frontend
npm install
npm run build

sudo systemctl restart labgoblin-updater.service
sleep 3
curl -sS http://127.0.0.1:8080/api/ready
```

## Development default login
- username: `admin`
- password: `admin`

`admin/admin` is for development only. Change credentials before production.

## Encryption key notes
- `CONFIG_ENCRYPTION_KEY` is stored in the LabGoblin `.env` file.
- Back up `CONFIG_ENCRYPTION_KEY`.
- Losing `CONFIG_ENCRYPTION_KEY` means encrypted Proxmox token secrets cannot be decrypted.
- Do not commit `.env`.
- Do not rotate `CONFIG_ENCRYPTION_KEY` casually after tokens are stored.

## Expected result
- `alembic heads` shows the current single head
- `alembic current` matches the current single head
- `python scripts/validate_deploy.py` passes
- `http://127.0.0.1:8080/api/ready` responds successfully

## Backup note
Use `pg_dump` before reset if any development data might need recovery.

## Scope note
This reset affects **application database records only**. It does not delete or modify Proxmox VM assets directly.
