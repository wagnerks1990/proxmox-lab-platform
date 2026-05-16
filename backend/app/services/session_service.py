from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.models import ConnectionLaunch, StudentVM, User, VMSession
from app.architecture.events import bus, DomainEvent, SESSION_CREATED, SESSION_EXPIRED
from app.architecture.state_machines import SessionState, SESSION_TRANSITIONS, validate_transition
from app.db.tx import safe_commit


class SessionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _set_state(self, row: VMSession, next_state: SessionState, *, reason: str | None = None) -> bool:
        current = SessionState(row.state)
        if not validate_transition(current, next_state, SESSION_TRANSITIONS):
            return False
        row.state = next_state.value
        now = datetime.now(timezone.utc)
        if next_state == SessionState.ACTIVE:
            row.launched_at = now
        elif next_state == SessionState.DISCONNECTED:
            row.disconnected_at = now
        elif next_state == SessionState.EXPIRED:
            row.expired_at = now
        elif next_state == SessionState.FAILED:
            row.failed_at = now
            row.failure_reason = reason
        row.updated_at = now
        return True

    def create_launching_session(self, user: User, vm: StudentVM, protocol: str, connection_launch_id: int | None = None, request_id: str | None = None) -> VMSession:
        row = VMSession(
            user_id=user.id, vm_id=vm.id, protocol=protocol, state=SessionState.LAUNCHING.value,
            node=vm.proxmox_node, proxmox_vmid=vm.vmid, connection_launch_id=connection_launch_id,
            request_id=request_id,
        )
        self.db.add(row)
        self.db.flush()
        bus.publish(DomainEvent(name=SESSION_CREATED, payload={'session_id': row.id, 'vm_id': vm.id, 'actor_id': user.id, 'protocol': protocol}))
        return row

    def mark_active(self, session_id: int) -> bool:
        row = self.db.query(VMSession).filter(VMSession.id == session_id).first()
        if not row:
            return False
        ok = self._set_state(row, SessionState.ACTIVE)
        if ok:
            safe_commit(self.db)
        return ok

    def mark_failed(self, session_id: int, reason: str | None = None) -> bool:
        row = self.db.query(VMSession).filter(VMSession.id == session_id).first()
        if not row:
            return False
        ok = self._set_state(row, SessionState.FAILED, reason=reason)
        if ok:
            safe_commit(self.db)
        return ok

    def mark_disconnected(self, session_id: int) -> bool:
        row = self.db.query(VMSession).filter(VMSession.id == session_id).first()
        if not row:
            return False
        ok = self._set_state(row, SessionState.DISCONNECTED)
        if ok:
            safe_commit(self.db)
        return ok

    def mark_reconnecting(self, session_id: int) -> bool:
        row = self.db.query(VMSession).filter(VMSession.id == session_id).first()
        if not row:
            return False
        ok = self._set_state(row, SessionState.RECONNECTING)
        if ok:
            safe_commit(self.db)
        return ok

    def mark_expired(self, session_id: int) -> bool:
        row = self.db.query(VMSession).filter(VMSession.id == session_id).first()
        if not row:
            return False
        ok = self._set_state(row, SessionState.EXPIRED)
        if ok:
            safe_commit(self.db)
            bus.publish(DomainEvent(name=SESSION_EXPIRED, payload={'session_id': row.id, 'vm_id': row.vm_id}))
        return ok

    def heartbeat(self, session_id: int) -> bool:
        row = self.db.query(VMSession).filter(VMSession.id == session_id).first()
        if not row:
            return False
        row.last_heartbeat_at = datetime.now(timezone.utc)
        row.updated_at = row.last_heartbeat_at
        safe_commit(self.db)
        return True

    def get_recent_activity(self, limit: int = 200):
        return self.db.query(VMSession).order_by(VMSession.created_at.desc()).limit(limit).all()

    def get_active_sessions(self, user_id: int | None = None):
        q = self.db.query(VMSession).filter(VMSession.state == SessionState.ACTIVE.value)
        if user_id is not None:
            q = q.filter(VMSession.user_id == user_id)
        return q.all()

    def expire_stale_sessions(self, stale_seconds: int = 900) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=stale_seconds)
        rows = self.db.query(VMSession).filter(VMSession.state.in_([SessionState.ACTIVE.value, SessionState.DISCONNECTED.value]), VMSession.last_heartbeat_at.isnot(None), VMSession.last_heartbeat_at < cutoff).all()
        count = 0
        for row in rows:
            if self._set_state(row, SessionState.EXPIRED):
                count += 1
        if count:
            safe_commit(self.db)
        return count

    # legacy helper retained
    def create_launch(self, user: User, vm: StudentVM, protocol: str, status: str = 'success', details: str | None = None, session_state: SessionState = SessionState.LAUNCHING) -> ConnectionLaunch:
        row = ConnectionLaunch(actor_id=user.id, vm_id=vm.id, protocol=protocol, status=status, details=details or f'state={session_state.value}')
        self.db.add(row)
        self.db.flush()
        return row
