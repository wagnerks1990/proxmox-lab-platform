from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.services.rbac import ROLE_STUDENT, STAFF_ROLES, get_role_name
from app.models.models import ConnectionLaunch, StudentVM, User, VMSession
from app.architecture.events import bus, DomainEvent, SESSION_CREATED, SESSION_EXPIRED, SESSION_STARTED, RECONNECT_ATTEMPT, RECONNECT_SUCCESS, RECONNECT_FAILURE, STALE_CLEANUP
from app.architecture.state_machines import SessionState, SESSION_TRANSITIONS, validate_transition
from app.db.tx import safe_commit
from app.core.config import settings
from app.security.reconnect_tokens import create_reconnect_token, verify_reconnect_token
from app.security.replay_store import build_replay_store


replay_store = build_replay_store(settings.replay_store_backend)


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

    @staticmethod
    def transition(current: SessionState, next_state: SessionState) -> bool:
        """Validate a session transition without accessing persistence."""
        return validate_transition(current, next_state, SESSION_TRANSITIONS)

    def create_launching_session(self, user: User, vm: StudentVM, protocol: str, connection_launch_id: int | None = None, request_id: str | None = None) -> VMSession:
        row = VMSession(organization_id=vm.organization_id, user_id=user.id, vm_id=vm.id, protocol=protocol, state=SessionState.LAUNCHING.value, node=vm.proxmox_node, proxmox_vmid=vm.vmid, connection_launch_id=connection_launch_id, request_id=request_id)
        self.db.add(row); self.db.flush()
        bus.publish(DomainEvent(name=SESSION_CREATED, payload={'organization_id': vm.organization_id, 'session_id': row.id, 'vm_id': vm.id, 'actor_id': user.id, 'protocol': protocol}))
        return row

    def get_session_for_user(self, session_id: int, user: User, organization_id: int | None = None, organization_role: str | None = None) -> VMSession | None:
        q = self.db.query(VMSession).filter(VMSession.id == session_id)
        if organization_id is not None:
            q = q.filter(VMSession.organization_id == organization_id)
        role = get_role_name(user)
        if organization_role == 'student' or (organization_role is None and role == ROLE_STUDENT):
            q = q.filter(VMSession.user_id == user.id)
        elif organization_role not in {'instructor', 'admin', 'owner'} and role not in STAFF_ROLES:
            return None
        return q.first()

    def mark_active(self, session_id: int) -> bool:
        row = self.db.query(VMSession).filter(VMSession.id == session_id).first()
        if not row: return False
        ok = self._set_state(row, SessionState.ACTIVE)
        if ok:
            safe_commit(self.db)
            bus.publish(DomainEvent(name=SESSION_STARTED, payload={'organization_id': getattr(row, 'organization_id', None), 'session_id': row.id, 'vm_id': row.vm_id}))
        return ok

    def mark_failed(self, session_id: int, reason: str | None = None) -> bool:
        row = self.db.query(VMSession).filter(VMSession.id == session_id).first()
        if not row: return False
        ok = self._set_state(row, SessionState.FAILED, reason=reason)
        if ok: safe_commit(self.db)
        return ok

    def mark_disconnected(self, session_id: int) -> bool:
        row = self.db.query(VMSession).filter(VMSession.id == session_id).first()
        if not row: return False
        ok = self._set_state(row, SessionState.DISCONNECTED)
        if ok: safe_commit(self.db)
        return ok

    def mark_reconnecting(self, session_id: int) -> bool:
        row = self.db.query(VMSession).filter(VMSession.id == session_id).first()
        if not row: return False
        bus.publish(DomainEvent(name=RECONNECT_ATTEMPT, payload={'organization_id': getattr(row, 'organization_id', None), 'session_id': row.id}))
        ok = self._set_state(row, SessionState.RECONNECTING)
        if ok: safe_commit(self.db)
        return ok

    def mark_expired(self, session_id: int) -> bool:
        row = self.db.query(VMSession).filter(VMSession.id == session_id).first()
        if not row: return False
        ok = self._set_state(row, SessionState.EXPIRED)
        if ok:
            safe_commit(self.db)
            bus.publish(DomainEvent(name=SESSION_EXPIRED, payload={'organization_id': getattr(row, 'organization_id', None), 'session_id': row.id, 'vm_id': row.vm_id}))
        return ok

    def heartbeat(self, session_id: int, next_state: SessionState | None = None) -> VMSession | None:
        row = self.db.query(VMSession).filter(VMSession.id == session_id).first()
        if not row: return None
        if row.state in {SessionState.EXPIRED.value, SessionState.FAILED.value}:
            return None
        if next_state is not None:
            self._set_state(row, next_state)
        row.last_heartbeat_at = datetime.now(timezone.utc)
        row.updated_at = row.last_heartbeat_at
        safe_commit(self.db)
        return row

    def get_recent_activity(self, limit: int = 200, organization_id: int | None = None):
        q = self.db.query(VMSession)
        if organization_id is not None:
            q = q.filter(VMSession.organization_id == organization_id)
        return q.order_by(VMSession.created_at.desc()).limit(limit).all()

    def get_active_sessions(self, user_id: int | None = None):
        q = self.db.query(VMSession).filter(VMSession.state == SessionState.ACTIVE.value)
        if user_id is not None: q = q.filter(VMSession.user_id == user_id)
        return q.all()

    def expire_stale_sessions(self, stale_seconds: int = 900) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=stale_seconds)
        rows = self.db.query(VMSession).filter(VMSession.state.in_([SessionState.ACTIVE.value, SessionState.DISCONNECTED.value, SessionState.RECONNECTING.value]), VMSession.last_heartbeat_at.isnot(None), VMSession.last_heartbeat_at < cutoff).all()
        count = 0
        for row in rows:
            if self._set_state(row, SessionState.EXPIRED): count += 1
        if count:
            safe_commit(self.db)
            bus.publish(DomainEvent(name=STALE_CLEANUP, payload={'expired_count': count}))
        return count

    def reconnect(self, session_id: int, reconnect_token: str, user_id: int) -> VMSession | None:
        row = self.db.query(VMSession).filter(VMSession.id == session_id).first()
        if not row or not self.verify_reconnect(reconnect_token, session_id, user_id, row.protocol):
            return None
        if not self.mark_reconnecting(session_id):
            bus.publish(DomainEvent(name=RECONNECT_FAILURE, payload={'organization_id': getattr(row, 'organization_id', None), 'session_id': session_id}))
            return None
        self.mark_active(session_id)
        bus.publish(DomainEvent(name=RECONNECT_SUCCESS, payload={'organization_id': getattr(row, 'organization_id', None), 'session_id': session_id}))
        return self.db.query(VMSession).filter(VMSession.id == session_id).first()

    def analytics_counts(self) -> dict[str, int]:
        active = self.db.query(func.count(VMSession.id)).filter(VMSession.state == SessionState.ACTIVE.value).scalar() or 0
        failed = self.db.query(func.count(VMSession.id)).filter(VMSession.state == SessionState.FAILED.value).scalar() or 0
        return {'active_sessions': int(active), 'failed_sessions': int(failed)}

    def protocol_usage_counts(self) -> dict[str, int]:
        rows = self.db.query(VMSession.protocol, func.count(VMSession.id)).group_by(VMSession.protocol).all()
        return {p: int(c) for p, c in rows}

    def create_launch(self, user: User, vm: StudentVM, protocol: str, status: str = 'success', details: str | None = None, session_state: SessionState = SessionState.LAUNCHING) -> ConnectionLaunch:
        row = ConnectionLaunch(actor_id=user.id, vm_id=vm.id, protocol=protocol, status=status, details=details or f'state={session_state.value}')
        self.db.add(row); self.db.flush(); return row


    def issue_reconnect_token(self, session_id: int, user_id: int, protocol: str) -> str:
        secret = settings.reconnect_token_secret or settings.jwt_secret_key
        return create_reconnect_token(secret=secret, session_id=session_id, user_id=user_id, protocol=protocol, ttl_seconds=settings.reconnect_token_ttl_seconds)

    def verify_reconnect(self, token: str, session_id: int, user_id: int, protocol: str) -> bool:
        secret = settings.reconnect_token_secret or settings.jwt_secret_key
        try:
            payload = verify_reconnect_token(token=token, secret=secret, session_id=session_id, user_id=user_id, protocol=protocol)
            return replay_store.mark_used(str(payload['jti']), int(payload['exp']))
        except Exception:
            return False

    def expire_reconnecting_sessions(self, timeout_seconds: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
        rows = self.db.query(VMSession).filter(VMSession.state == SessionState.RECONNECTING.value, VMSession.updated_at < cutoff).all()
        count = 0
        for row in rows:
            if self._set_state(row, SessionState.EXPIRED):
                count += 1
        if count:
            safe_commit(self.db)
        return count

    def fail_stuck_launching(self, timeout_seconds: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
        rows = self.db.query(VMSession).filter(VMSession.state == SessionState.LAUNCHING.value, VMSession.created_at < cutoff).all()
        count = 0
        for row in rows:
            if self._set_state(row, SessionState.FAILED, reason='launch timeout'):
                count += 1
        if count:
            safe_commit(self.db)
        return count
