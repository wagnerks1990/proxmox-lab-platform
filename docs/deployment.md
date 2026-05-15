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

## Nginx
- Reload/restart Nginx after config/static updates.

## Rollback
- Revert release commit.
- Downgrade migration if needed.
- Restart backend and nginx.
