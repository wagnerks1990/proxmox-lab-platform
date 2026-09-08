from app.main import app


def _has(paths, suffix):
    return any(p.endswith(suffix) for p in paths)


def test_key_routes_registered():
    paths = set(app.openapi()['paths'])
    required_suffixes = [
        '/auth/login', '/auth/me', '/vms', '/vms/{id}/console/terminal-url',
        '/admin/session-activity', '/admin/telemetry/summary', '/admin/runtime/summary',
        '/admin/validation/summary', '/pools', '/pools/{id}/plan', '/admin/reconciliation/preview',
        '/ready', '/admin/system/update', '/admin/system/update/apply', '/admin/system/update/rollback',
        '/classroom/assignments', '/admin/lab-runs', '/admin/lab-runs/{run_id}/assignments/bulk',
    ]
    missing = [s for s in required_suffixes if not _has(paths, s)]
    assert not missing, f'missing suffixes: {missing}'
