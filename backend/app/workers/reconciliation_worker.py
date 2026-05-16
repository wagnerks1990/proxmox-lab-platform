from app.workers.locks import acquire_worker_lock, release_worker_lock


def run_once() -> dict[str, str]:
    name = 'reconciliation_worker'
    if not acquire_worker_lock(name):
        return {'state': 'skipped_overlap'}
    try:
        return {'state': 'placeholder_safe'}
    finally:
        release_worker_lock(name)
