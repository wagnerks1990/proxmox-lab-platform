from jose import jwt
from fastapi import HTTPException

from app.api.deps import get_user_from_token


class _Query:
    def __init__(self, user):
        self._user = user

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._user


class _DB:
    def __init__(self, user):
        self._user = user

    def query(self, _model):
        return _Query(self._user)


class _User:
    def __init__(self, username):
        self.username = username


def test_get_user_from_token_valid(monkeypatch):
    from app.api import deps

    monkeypatch.setattr(deps.settings, 'jwt_secret_key', 'test-secret')
    monkeypatch.setattr(deps.settings, 'jwt_algorithm', 'HS256')

    token = jwt.encode({'sub': 'alice'}, deps.settings.jwt_secret_key, algorithm=deps.settings.jwt_algorithm)
    user = get_user_from_token(token, _DB(_User('alice')))

    assert user.username == 'alice'


def test_get_user_from_token_invalid_returns_401(monkeypatch):
    from app.api import deps

    monkeypatch.setattr(deps.settings, 'jwt_secret_key', 'test-secret')
    monkeypatch.setattr(deps.settings, 'jwt_algorithm', 'HS256')

    bad_token = jwt.encode({'sub': 'alice'}, 'other-secret', algorithm='HS256')

    try:
        get_user_from_token(bad_token, _DB(_User('alice')))
        assert False, 'expected HTTPException for invalid token'
    except HTTPException as exc:
        assert exc.status_code == 401
        assert exc.detail == 'Invalid token'
