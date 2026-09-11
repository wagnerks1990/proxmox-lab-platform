#!/usr/bin/env bash
set -euo pipefail

echo "=== LabGoblin: Codex Cloud Check ==="

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
test -f backend/scripts/validate_post_reset_state.py && echo "backend/scripts/validate_post_reset_state.py present" || echo "backend/scripts/validate_post_reset_state.py missing"
test -f backend/scripts/seed_dev_admin.py && echo "backend/scripts/seed_dev_admin.py present" || echo "backend/scripts/seed_dev_admin.py missing"
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

echo "=== Alembic static DAG check ==="
python3 - <<'PYCODE'
import ast
from pathlib import Path

versions_dir = Path('backend/alembic/versions')
revision_to_down = {}
revisions = []
for path in sorted(versions_dir.glob('*.py')):
    mod = ast.parse(path.read_text(), filename=str(path))
    rev = None
    down = None
    for node in mod.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == 'revision' and isinstance(node.value, ast.Constant):
                    rev = node.value.value
                if isinstance(t, ast.Name) and t.id == 'down_revision':
                    if isinstance(node.value, ast.Constant):
                        down = node.value.value
                    elif isinstance(node.value, (ast.Tuple, ast.List)):
                        down = tuple(e.value for e in node.value.elts if isinstance(e, ast.Constant))
    if rev:
        revisions.append(rev)
        revision_to_down[rev] = down

seen = set()
duplicates = []
for r in revisions:
    if r in seen:
        duplicates.append(r)
    seen.add(r)

all_down = set()
for d in revision_to_down.values():
    if d is None:
        continue
    if isinstance(d, tuple):
        all_down.update(x for x in d if x)
    else:
        all_down.add(d)
heads = sorted([r for r in revisions if r not in all_down])

print('revisions:', revisions)
print('down_revisions:', revision_to_down)
print('duplicate revision IDs:', duplicates if duplicates else 'none')
print('calculated heads:', heads)

if duplicates:
    raise SystemExit('FAIL: duplicate Alembic revision IDs found')
if len(heads) != 1:
    raise SystemExit(f'FAIL: expected exactly one Alembic head, found {heads}')
print('single alembic head:', heads[0])
PYCODE

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
