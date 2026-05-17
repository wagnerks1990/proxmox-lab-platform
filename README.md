# Proxmox Lab Access Platform

Full-stack starter platform for managing student access to Proxmox lab resources.

## Stack
- Frontend: React + Vite (Tailwind-ready)
- Backend: FastAPI + SQLAlchemy
- DB: PostgreSQL
- Auth: JWT + bcrypt password hashing

## Project structure
- `backend/app/main.py` – FastAPI entrypoint
- `backend/app/api/routes.py` – REST endpoints
- `backend/app/models/models.py` – relational models (`users`, `roles`, `vm_templates`, `student_vms`, `permissions`, `audit_logs`)
- `backend/app/services/proxmox.py` – secure backend-only Proxmox API client
- `backend/init.sql` – seed data
- `frontend/src/main.jsx` – login + role dashboard + template list + VM create UI

## First working features implemented
- Login endpoint and JWT auth
- Role loading (`Student`, `Teacher`, `Admin`)
- Student-scoped template listing
- VM list endpoint (student sees own; teacher/admin sees all)
- VM provisioning endpoint via Proxmox clone/start API
- Audit log write on VM creation
- Frontend pages: Login, Dashboard, My VMs, Create VM

## API design (v1)
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/templates`
- `GET /api/vms`
- `POST /api/vms`

Planned next endpoints (not fully implemented yet):
- start/stop/reboot/delete/status
- admin user/class/permission/audit CRUD

## Setup
1. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.db.bootstrap
# seed with init.sql using psql
uvicorn app.main:app --reload
```

2. Frontend
```bash
cd frontend
npm install
npm run dev
```

## Seed users
All seeded users use password: `Password123!`
- `alice` (Student)
- `teacher1` (Teacher)
- `admin1` (Admin)

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
- Student template access enforced with `permissions` table.
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

## Future expansion-ready
Architecture leaves space for:
- class/group and quota tables
- scheduled cleanup jobs
- snapshots
- VLAN/private network workflows
- SSO providers
- embedded noVNC
