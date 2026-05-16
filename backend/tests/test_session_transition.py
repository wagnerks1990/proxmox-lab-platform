from app.architecture.state_machines import SessionState
from app.services.session_service import SessionService


def test_session_transition_validation_only():
    svc = SessionService(db=None)  # validation path does not access db
    assert svc.transition(SessionState.LAUNCHING, SessionState.ACTIVE)
    assert not svc.transition(SessionState.ACTIVE, SessionState.LAUNCHING)
