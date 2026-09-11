#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is required. $2"
}

require_python_module() {
  python3 -c "import $1" >/dev/null 2>&1 || fail "Python module '$1' is required. $2"
}

require_command git "Install Git and rerun validation."
require_command python3 "Install Python 3.12 and rerun validation."

echo "=== LabGoblin repository validation ==="
echo "=== Git status (preservation warning only) ==="
git status --short
if [ -n "$(git status --short)" ]; then
  echo "WARNING: working tree is not clean; preserve unrelated changes."
fi

echo "=== Required repository structure ==="
required_paths=(
  AGENTS.md AI_CONTEXT.md .gitignore mkdocs.yml docker-compose.yml
  docker-compose.live-test.yml docs/brand.md scripts/check_branding.py
  scripts/check_repository_hygiene.py scripts/export_openapi.py backend/app
  backend/alembic backend/alembic.ini backend/requirements.txt
  backend/requirements-dev.txt backend/tests
  backend/tests/test_all_runtime_modules_import.py frontend/package.json
  frontend/package-lock.json frontend/openapi.json
  frontend/src/generated/api-schema.d.ts
)
for path in "${required_paths[@]}"; do
  [ -e "$path" ] || fail "required path is missing: $path"
  echo "present: $path"
done

require_command npm "Install Node.js 22 with npm and run 'npm ci --prefix frontend'."
require_command docker "Install Docker with the Compose v2 plugin."
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required. Install the compose plugin."
require_python_module pytest "Install backend/requirements-dev.txt."
require_python_module ruff "Install backend/requirements-dev.txt."
require_python_module bandit "Install backend/requirements-dev.txt."
require_python_module pip_audit "Install backend/requirements-dev.txt."
require_python_module alembic "Install backend/requirements.txt."
require_python_module mkdocs "Install mkdocs==1.6.1."
[ -d frontend/node_modules ] || fail "frontend dependencies are missing. Run 'npm ci --prefix frontend'."

export PYTHONPATH="$ROOT/backend${PYTHONPATH:+:$PYTHONPATH}"
export DATABASE_URL="sqlite+pysqlite:///:memory:"
export JWT_SECRET_KEY="cloud-validation-only-jwt-secret"
export CONFIG_ENCRYPTION_KEY="cloud-validation-only-config-key"
export PROXMOX_BASE_URL="https://127.0.0.1:8006/api2/json"
export PROXMOX_TOKEN_ID="validation@pve!labgoblin"
export PROXMOX_TOKEN_SECRET="cloud-validation-only-token"
export WORKER_SCHEDULER_ENABLED=false

echo "=== Repository and branding hygiene ==="
python3 scripts/check_branding.py
python3 scripts/check_repository_hygiene.py

echo "=== Shell and Compose syntax ==="
sh -n deploy/install.sh backend/docker-entrypoint.sh scripts/generate_api_contract.sh
bash -n scripts/codex_cloud_check.sh scripts/deploy.sh scripts/backend-restart.sh scripts/frontend-build.sh
docker compose -f docker-compose.yml -f docker-compose.live-test.yml config --quiet

echo "=== Backend compile, lint, security, and tests ==="
python3 -m compileall -q backend/app backend/tests deploy scripts tests
python3 -m ruff format --check backend/app backend/tests deploy scripts tests
python3 -m ruff check backend/app backend/tests deploy scripts tests
python3 -m bandit -r backend/app deploy -ll -q
python3 -m pip_audit -r backend/requirements.txt
python3 -m alembic -c backend/alembic.ini heads
python3 -m alembic -c backend/alembic.ini history
python3 -m pytest -q --disable-warnings backend/tests

echo "=== Frontend tests, build, and dependency audit ==="
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend audit --audit-level=moderate

echo "=== Generated API contract drift ==="
contract_dir=$(mktemp -d)
trap 'rm -r -- "$contract_dir"' EXIT
python3 scripts/export_openapi.py "$contract_dir/openapi.json"
(
  cd frontend
  npx --no-install openapi-typescript "$contract_dir/openapi.json" -o "$contract_dir/api-schema.d.ts"
)
if ! diff -u frontend/openapi.json "$contract_dir/openapi.json"; then
  fail "frontend/openapi.json is stale. Run scripts/generate_api_contract.sh and commit the result."
fi
if ! diff -u frontend/src/generated/api-schema.d.ts "$contract_dir/api-schema.d.ts"; then
  fail "frontend/src/generated/api-schema.d.ts is stale. Run scripts/generate_api_contract.sh and commit the result."
fi

echo "=== Strict documentation build ==="
python3 -m mkdocs build --strict

echo "=== LabGoblin repository validation passed ==="
echo "Live Proxmox, browser-console, TLS, systemd, nginx, update-recovery, and backup-restore acceptance remain separate deployment-environment gates."
