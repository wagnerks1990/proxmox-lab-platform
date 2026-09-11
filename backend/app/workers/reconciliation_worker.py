import asyncio

from app.db.session import SessionLocal
from app.models.models import StudentVM
from app.services.proxmox import ProxmoxClient
from app.services.operation_service import _is_not_found
from app.workers.locks import acquire_worker_lock, release_worker_lock
from app.services.worker_run_service import WorkerRunService


async def _reconcile(db) -> dict[str, int]:
    rows = db.query(StudentVM).filter(StudentVM.deleted_at.is_(None)).all()
    matched = missing = updated = observation_errors = 0
    for vm in rows:
        previous = vm.status
        if vm.proxmox_cluster_id is None:
            observation_errors += 1
            continue
        try:
            proxmox = ProxmoxClient(vm.proxmox_cluster_id)
            live = await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)
            vm.status = live.get("status", vm.status)
            matched += 1
        except Exception as exc:
            if _is_not_found(exc):
                vm.status = "missing"
                missing += 1
            else:
                observation_errors += 1
        updated += int(previous != vm.status)
    db.commit()
    return {
        "checked": len(rows),
        "matched": matched,
        "missing": missing,
        "observation_errors": observation_errors,
        "status_updated": updated,
    }


def run_once() -> dict[str, int | str]:
    name = "reconciliation_worker"
    if not acquire_worker_lock(name):
        return {"state": "skipped_overlap"}
    db = SessionLocal()
    run = WorkerRunService(db).start(name)
    try:
        out = asyncio.run(_reconcile(db))
        WorkerRunService(db).finish(run.id, "success", out)
        return out
    finally:
        db.close()
        release_worker_lock(name)
