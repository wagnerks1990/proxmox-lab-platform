#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
: "${DATABASE_URL:=sqlite+pysqlite:///:memory:}"
: "${JWT_SECRET_KEY:=openapi-generation-only-secret-key}"
: "${PROXMOX_BASE_URL:=https://127.0.0.1:8006/api2/json}"
: "${PROXMOX_TOKEN_ID:=openapi@pve!generation}"
: "${PROXMOX_TOKEN_SECRET:=openapi-generation-only-token}"
export DATABASE_URL JWT_SECRET_KEY PROXMOX_BASE_URL PROXMOX_TOKEN_ID PROXMOX_TOKEN_SECRET
PYTHONPATH="$ROOT/backend" python "$ROOT/scripts/export_openapi.py" "$ROOT/frontend/openapi.json"
cd "$ROOT/frontend"
npm run generate:api
