import jwt
from fastapi import HTTPException

from app.api.deps import get_user_from_token
from app.models.models import AuthSession


class _Query:
    def __init__(self, user):
        self._user = user

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._user


class _DB:
    def __init__(self, user, session=None):
        self._user = user
        self._session = session

    def query(self, model):
        return _Query(self._session if model is AuthSession else self._user)


class _User:
    def __init__(self, username):
        self.id = 1
        self.username = username
        self.token_version = 1
        self.is_active = True


class _Session:
    user_id = 1
    revoked_at = None
    expires_at = None


def test_get_user_from_token_valid(monkeypatch):
    from app.api import deps

    monkeypatch.setattr(deps.settings, "jwt_secret_key", "test-secret")
    monkeypatch.setattr(deps.settings, "jwt_algorithm", "HS256")

    token = jwt.encode(
        {"sub": "alice", "jti": "session-1", "ver": 1, "typ": "access"},
        deps.settings.jwt_secret_key,
        algorithm=deps.settings.jwt_algorithm,
    )
    user = get_user_from_token(token, _DB(_User("alice"), _Session()))

    assert user.username == "alice"


def test_get_user_from_token_invalid_returns_401(monkeypatch):
    from app.api import deps

    monkeypatch.setattr(deps.settings, "jwt_secret_key", "test-secret")
    monkeypatch.setattr(deps.settings, "jwt_algorithm", "HS256")

    bad_token = jwt.encode({"sub": "alice"}, "other-secret", algorithm="HS256")

    try:
        get_user_from_token(bad_token, _DB(_User("alice")))
        assert False, "expected HTTPException for invalid token"
    except HTTPException as exc:
        assert exc.status_code == 401
        assert exc.detail == "Invalid token"
