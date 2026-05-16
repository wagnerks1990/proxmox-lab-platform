# Database Migrations (Alembic)

## Runtime behavior
`backend/alembic/env.py` loads `settings.database_url` from app settings and applies it to Alembic config at runtime.

## Standard commands
From `backend/`:
- `alembic revision -m "message"`
- `alembic upgrade head`
- `alembic downgrade -1`

## Notes
- Keep migration scripts idempotent where practical (e.g., optional column checks).
- Do not rely on manual `ALTER TABLE` instructions for tracked schema changes.
