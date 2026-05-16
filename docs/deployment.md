# Deployment Guide

## Backend deploy
1. Pull code.
2. Install/update Python dependencies.
3. Run migrations (`alembic upgrade head`).
4. Restart backend service.

## Frontend deploy
1. Install dependencies.
2. Build frontend bundle.
3. Publish build artifacts to web root.

## Local Guacamole integration (same Ubuntu host)
Expected local defaults:
- `GUACAMOLE_INTERNAL_URL=http://127.0.0.1:8080/guacamole`
- `GUACAMOLE_BASE_URL=/guacamole`

Backend status endpoint:
- `GET /api/admin/guacamole/status`
- Performs safe reachability check (no login required)
- Does not expose credentials

## Nginx reverse proxy notes
Serve app + Guacamole on same host:
- platform frontend/API under `/`
- Guacamole under `/guacamole`

Example concept:
- `location / { ...platform... }`
- `location /guacamole/ { proxy_pass http://127.0.0.1:8080/guacamole/; ... }`

## Rollback
- Revert release commit.
- Downgrade migration if needed.
- Restart backend and nginx.

## Optional Docker note
Docker Compose examples may be used as reference only, not required for local-host Guacamole deployments.
