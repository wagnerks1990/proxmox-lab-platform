from sqlalchemy.orm import Session
from app.models.models import ConnectionLaunch, StudentVM, User
from app.architecture.events import bus, DomainEvent, SESSION_CREATED
from app.architecture.state_machines import SessionState, SESSION_TRANSITIONS, validate_transition
from app.db.tx import safe_commit


class SessionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_launch(self, user: User, vm: StudentVM, protocol: str, status: str = 'success', details: str | None = None, session_state: SessionState = SessionState.LAUNCHING) -> ConnectionLaunch:
        details_text = details or f'state={session_state.value}'
        row = ConnectionLaunch(actor_id=user.id, vm_id=vm.id, protocol=protocol, status=status, details=details_text)
        self.db.add(row)
        self.db.flush()
        bus.publish(DomainEvent(name=SESSION_CREATED, payload={'vm_id': vm.id, 'actor_id': user.id, 'protocol': protocol}))
        return row

    def transition(self, current: SessionState, next_state: SessionState) -> bool:
        return validate_transition(current, next_state, SESSION_TRANSITIONS)

    def list_recent(self, limit: int = 200):
        return self.db.query(ConnectionLaunch).order_by(ConnectionLaunch.created_at.desc()).limit(limit).all()

    def transition_persist(self, launch_id: int, current: SessionState, next_state: SessionState) -> bool:
        if not self.transition(current, next_state):
            return False
        row = self.db.query(ConnectionLaunch).filter(ConnectionLaunch.id == launch_id).first()
        if not row:
            return False
        row.details = f'state={next_state.value}'
        safe_commit(self.db)
        return True
