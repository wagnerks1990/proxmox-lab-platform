import asyncio

from app.db.session import SessionLocal
from app.models.models import StudentVM
from app.services.proxmox import ProxmoxClient
from app.workers.locks import acquire_worker_lock, release_worker_lock
from app.services.worker_run_service import WorkerRunService


async def _reconcile(db) -> dict[str, int]:
    rows = db.query(StudentVM).all()
    matched = missing = updated = 0
    proxmox = ProxmoxClient()
    for vm in rows:
        previous = vm.status
        try:
            live = await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)
            vm.status = live.get("status", vm.status)
            matched += 1
        except Exception:
            vm.status = (
                "missing" if vm.status not in {"error", "missing"} else vm.status
            )
            missing += 1
        updated += int(previous != vm.status)
    db.commit()
    return {
        "checked": len(rows),
        "matched": matched,
        "missing": missing,
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
