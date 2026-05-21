#!/usr/bin/env bash
set -euo pipefail

echo "=== Proxmox Lab Platform: Codex Cloud Check ==="

echo "=== Git status ==="
git status --short

if [ -n "$(git status --short)" ]; then
  echo "Working tree is not clean. Review changes carefully."
fi

echo "=== Repository structure ==="
test -f AGENTS.md && echo "AGENTS.md present" || echo "AGENTS.md missing"
test -f .gitignore && echo ".gitignore present" || echo ".gitignore missing"
test -d docs && echo "docs/ present" || echo "docs/ missing"
test -d scripts && echo "scripts/ present" || echo "scripts/ missing"
test -f backend/requirements.txt && echo "backend/requirements.txt present" || echo "backend/requirements.txt missing"
test -f frontend/package.json && echo "frontend/package.json present" || echo "frontend/package.json missing"
test -f frontend/package-lock.json && echo "frontend/package-lock.json present" || echo "frontend/package-lock.json missing"
test -d backend/alembic && echo "backend/alembic present" || echo "backend/alembic missing"

echo "=== Backend compile check ==="
if [ -d backend/app ]; then
  cd backend
  if command -v python >/dev/null 2>&1; then
    python -m compileall app
  elif command -v python3 >/dev/null 2>&1; then
    python3 -m compileall app
  else
    echo "Python not found; skipping backend compile."
  fi
  cd ..
else
  echo "backend/app not found; skipping backend compile."
fi

echo "=== Alembic structure check ==="
if [ -d backend/alembic ]; then
  cd backend
  if command -v alembic >/dev/null 2>&1; then
    alembic heads || true
    alembic history | tail -n 30 || true
  else
    echo "alembic command not found; skipping Alembic heads/history."
  fi
  cd ..
else
  echo "backend/alembic not found; skipping Alembic check."
fi

echo "=== Frontend build availability check ==="
if [ -f frontend/package.json ]; then
  cd frontend
  if [ -d node_modules ]; then
    npm run build
  else
    echo "frontend/node_modules not found; skipping npm run build."
    echo "Install dependencies with npm ci or npm install before running frontend build."
  fi
  cd ..
else
  echo "frontend/package.json not found; skipping frontend build."
fi

echo "=== Cloud check complete ==="
echo "Not validated in Codex Cloud:"
echo "- live production PostgreSQL state"
echo "- production Alembic current revision"
echo "- nginx"
echo "- systemd"
echo "- live Proxmox API"
echo "- live SSE browser behavior"
echo "- live Guacamole/ttyd"
echo "- production browser login"
echo "- actual VM lifecycle behavior on the Proxmox cluster"
