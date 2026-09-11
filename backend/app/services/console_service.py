from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.models import StudentVM, User, AuditLog
from app.db.tx import safe_commit
from app.architecture.idempotency import store as idempotency_store
from app.architecture.policies import can_launch_vm, PolicyError
from app.core.config import settings


class ConsoleService:
    def __init__(self, db: Session):
        self.db = db

    def _ensure_running_or_stopped(self, vm: StudentVM):
        if vm.status not in {"running", "stopped", "provisioning", "error"}:
            raise HTTPException(
                status_code=400, detail={"error": "VM state not launchable."}
            )

    async def terminal_url(self, user: User, vm: StudentVM):
        if not settings.ssh_terminal_enabled:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "SSH terminal access is disabled until per-assignment credentials and trusted IP binding are configured."
                },
            )
        try:
            can_launch_vm(user, vm)
        except PolicyError as exc:
            raise HTTPException(status_code=403, detail={"error": str(exc)})
        key = f"launch:{user.id}:{vm.id}:web_terminal"
        if not idempotency_store.reserve(key):
            raise HTTPException(
                status_code=409,
                detail={"error": "Duplicate launch request in progress."},
            )
        try:
            if not vm.ssh_enabled:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "WEB TERMINAL is not enabled for this VM."},
                )
            if not vm.assigned_ip:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "No IP address found for WEB TERMINAL."},
                )
            self.db.add(
                AuditLog(
                    organization_id=vm.organization_id,
                    actor_id=user.id,
                    action="console_web_terminal",
                    target_type="student_vm",
                    target_id=str(vm.vmid),
                )
            )
            safe_commit(self.db)
            return {
                "type": "web_terminal",
                "launch_url": f"/terminal/{vm.id}",
                "protocol": "WEB_TERMINAL",
                "state": "launching",
                "heartbeat_interval_seconds": 30,
                "expires_at": None,
            }
        finally:
            idempotency_store.release(key)
