#!/usr/bin/env bash
set -euo pipefail

echo "[WARNING] This will permanently destroy DEVELOPMENT app database data in the target database schema."
echo "[WARNING] This is intended for development reset workflows only."

if [[ "${RESET_DEV_DB_CONFIRM:-}" != "YES" ]]; then
  echo "Refusing to continue. Set RESET_DEV_DB_CONFIRM=YES to proceed."
  exit 1
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required. Export DATABASE_URL and re-run."
  exit 1
fi

echo "Resetting PostgreSQL public schema from DATABASE_URL target..."
python3 - <<'PY'
import os
from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
engine = create_engine(url)
with engine.begin() as conn:
    conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
    conn.execute(text("CREATE SCHEMA public"))
print("Schema reset complete.")
PY

echo "Running Alembic migrations..."
alembic upgrade heads

echo "Alembic heads:"
alembic heads

echo "Alembic current:"
alembic current
