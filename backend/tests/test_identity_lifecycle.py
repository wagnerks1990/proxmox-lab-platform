from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.models.models import AuditLog, AuthLoginAttempt, AuthSession, Role, User
from app.services.security import hash_password


def _setup():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(engine)
    db = TestingSession()
    role = Role(name='Admin')
    db.add(role); db.flush()
    user = User(
        username='admin',
        email='admin@example.com',
        password_hash=hash_password('OriginalPass1!'),
        role_id=role.id,
        role='Admin',
        is_active=True,
    )
    db.add(user); db.commit()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return engine, db, user, TestClient(app)


def _login(client, password='OriginalPass1!'):
    return client.post('/api/auth/login', json={'username': 'admin', 'password': password})


def _bearer(token):
    return {'Authorization': f'Bearer {token}'}


def _teardown(engine, db):
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(engine)


def test_login_logout_and_structured_audit_event():
    engine, db, user, client = _setup()
    try:
        login = _login(client)
        assert login.status_code == 200
        token = login.json()['access_token']
        assert client.get('/api/auth/me', headers=_bearer(token)).status_code == 200
        session = db.query(AuthSession).filter(AuthSession.user_id == user.id).one()
        assert session.revoked_at is None

        logout = client.post('/api/auth/logout', headers=_bearer(token))
        assert logout.status_code == 204
        assert client.get('/api/auth/me', headers=_bearer(token)).status_code == 401
        events = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
        assert [event.action for event in events] == ['identity.login', 'identity.logout']
        assert all(event.outcome == 'success' for event in events)
    finally:
        _teardown(engine, db)


def test_password_change_revokes_old_token_and_clears_forced_change():
    engine, db, user, client = _setup()
    try:
        first_token = _login(client).json()['access_token']
        user.force_password_change = True
        db.commit()
        assert client.get('/api/vms', headers=_bearer(first_token)).status_code == 403

        changed = client.post('/api/auth/change-password', headers=_bearer(first_token), json={
            'current_password': 'OriginalPass1!',
            'new_password': 'ReplacementPass2!',
        })
        assert changed.status_code == 200
        replacement_token = changed.json()['access_token']
        assert client.get('/api/auth/me', headers=_bearer(first_token)).status_code == 401
        me = client.get('/api/auth/me', headers=_bearer(replacement_token))
        assert me.status_code == 200
        assert me.json()['force_password_change'] is False
        assert user.token_version == 2
        assert db.query(AuthSession).filter(AuthSession.user_id == user.id, AuthSession.revoked_at.is_not(None)).count() == 1
    finally:
        _teardown(engine, db)


def test_failed_login_throttle_is_persistent_and_audited(monkeypatch):
    engine, db, _user, client = _setup()
    monkeypatch.setattr(settings, 'login_max_failures', 3)
    try:
        for _ in range(3):
            assert _login(client, 'wrong-password').status_code == 401
        blocked = _login(client)
        assert blocked.status_code == 429
        assert int(blocked.headers['retry-after']) > 0
        assert db.query(AuthLoginAttempt).count() == 1
        failures = db.query(AuditLog).filter(AuditLog.action == 'identity.login', AuditLog.outcome == 'failure').all()
        assert len(failures) == 3
        assert all('wrong-password' not in (event.metadata_json or '') for event in failures)
    finally:
        _teardown(engine, db)


def test_admin_password_reset_revokes_target_sessions():
    engine, db, admin, client = _setup()
    try:
        role = db.query(Role).filter(Role.name == 'Admin').one()
        student = User(username='student', email='student@example.com', password_hash=hash_password('StudentPass1!'), role_id=role.id, role='Admin', is_active=True)
        db.add(student); db.commit()
        admin_token = _login(client).json()['access_token']
        student_login = client.post('/api/auth/login', json={'username': 'student', 'password': 'StudentPass1!'}).json()['access_token']

        reset = client.patch(f'/api/admin/users/{student.id}/password', headers=_bearer(admin_token), json={'password': 'ResetStudent2!', 'force_password_change': True})
        assert reset.status_code == 200
        assert client.get('/api/auth/me', headers=_bearer(student_login)).status_code == 401
        assert student.force_password_change is True
        event = db.query(AuditLog).filter(AuditLog.action == 'identity.password_reset').one()
        assert event.actor_id == admin.id
        assert 'sessions_revoked' in event.metadata_json
    finally:
        _teardown(engine, db)
