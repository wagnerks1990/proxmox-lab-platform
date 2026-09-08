# Development validation

Run from the repository root with safe test-only environment values:

```bash
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
PYTHONPATH=backend alembic -c backend/alembic.ini upgrade head
PYTHONPATH=backend pytest -q backend/tests
ruff check --select E9,F63,F7,F82 backend/app backend/tests deploy scripts
bandit -r backend/app deploy -lll -q
pip-audit -r backend/requirements.txt
cd frontend && npm ci && npm test && npm run build && npm audit --omit=dev
```

Regenerate the API contract after route or schema changes:

```bash
scripts/generate_api_contract.sh
```

CI fails if `frontend/openapi.json` or `frontend/src/generated/api-schema.d.ts` drifts. Generated types are the frontend/backend contract; do not maintain a conflicting handwritten schema.

These checks do not validate a live Proxmox cluster, host networking, systemd permissions, browser compatibility, or real backup restoration.
