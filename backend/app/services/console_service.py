from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.models import StudentVM, User, AuditLog
from app.services.proxmox import ProxmoxClient
from app.services.session_service import SessionService
from app.architecture.idempotency import store as idempotency_store
from app.architecture.policies import can_launch_vm, PolicyError


class ConsoleService:
    def __init__(self, db: Session):
        self.db = db
        self.proxmox = ProxmoxClient()
        self.sessions = SessionService(db)

    def _ensure_running_or_stopped(self, vm: StudentVM):
        if vm.status not in {'running', 'stopped', 'provisioning', 'error'}:
            raise HTTPException(status_code=400, detail={'error': 'VM state not launchable.'})

    async def terminal_url(self, user: User, vm: StudentVM):
        try:
            can_launch_vm(user, vm)
        except PolicyError as exc:
            raise HTTPException(status_code=403, detail={'error': str(exc)})
        key = f'launch:{user.id}:{vm.id}:web_terminal'
        if not idempotency_store.reserve(key):
            raise HTTPException(status_code=409, detail={'error': 'Duplicate launch request in progress.'})
        try:
            if not vm.ssh_enabled:
                self.sessions.create_launch(user, vm, 'WEB_TERMINAL', 'failed', 'web terminal disabled')
                self.db.commit()
                raise HTTPException(status_code=400, detail={'error': 'WEB TERMINAL is not enabled for this VM.'})
            if not vm.assigned_ip:
                self.sessions.create_launch(user, vm, 'WEB_TERMINAL', 'failed', 'missing assigned IP')
                self.db.commit()
                raise HTTPException(status_code=400, detail={'error': 'No IP address found for WEB TERMINAL.'})
            self.db.add(AuditLog(actor_id=user.id, action='console_web_terminal', target_type='student_vm', target_id=str(vm.vmid)))
            self.sessions.create_launch(user, vm, 'WEB_TERMINAL', 'success', vm.assigned_ip)
            self.db.commit()
            return {'type': 'web_terminal', 'url': f'http://10.0.16.162:7681/?arg={vm.assigned_ip}'}
        finally:
            idempotency_store.release(key)
