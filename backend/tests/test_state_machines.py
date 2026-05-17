from app.architecture.state_machines import SessionState, SESSION_TRANSITIONS, validate_transition


def test_valid_transition():
    assert validate_transition(SessionState.LAUNCHING, SessionState.ACTIVE, SESSION_TRANSITIONS)


def test_invalid_transition():
    assert not validate_transition(SessionState.ACTIVE, SessionState.LAUNCHING, SESSION_TRANSITIONS)
