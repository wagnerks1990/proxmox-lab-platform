from app.workers.locks import acquire_worker_lock, release_worker_lock


def run_once() -> dict[str, int]:
    name = 'cleanup_worker'
    if not acquire_worker_lock(name):
        return {'skipped_overlap': 1}
    try:
        return {'expired_launch_artifacts_cleaned': 0}
    finally:
        release_worker_lock(name)
