from app.db.session import SessionLocal
from app.services.proxmox import ProxmoxClient
from app.workers.locks import acquire_worker_lock, release_worker_lock


def run_once() -> dict[str, str]:
    name = 'health_worker'
    if not acquire_worker_lock(name):
        return {'state': 'skipped_overlap'}
    db = SessionLocal()
    try:
        db.execute('SELECT 1')
        return {'database': 'ok', 'proxmox': 'unknown', 'guacamole': 'unknown'}
    except Exception:
        return {'database': 'error', 'proxmox': 'unknown', 'guacamole': 'unknown'}
    finally:
        db.close()
        release_worker_lock(name)
