#!/usr/bin/env bash
set -euo pipefail

echo "Manual deployment helper (not auto-run in Codex)"
echo "1) backend: install deps + alembic upgrade head + restart service"
echo "2) frontend: npm ci && npm run build"
echo "3) reload nginx"
