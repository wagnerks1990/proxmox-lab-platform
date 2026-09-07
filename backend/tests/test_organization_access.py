from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.organization_access import (
    ORGANIZATION_ROLES,
    normalize_organization_role,
    require_organization_access,
)


class _Query:
    def __init__(self, result):
        self.result = result

    def filter(self, *_args):
        return self

    def first(self):
        return self.result


class _Db:
    def __init__(self, organization, membership=None):
        self.results = [organization, membership]

    def query(self, _model):
        return _Query(self.results.pop(0))


def _user(role_name, user_id=7):
    return SimpleNamespace(id=user_id, role='Student', role_rel=SimpleNamespace(name=role_name))


def test_organization_roles_are_explicit_and_normalized():
    assert ORGANIZATION_ROLES == ('student', 'instructor', 'admin', 'owner')
    assert normalize_organization_role(' Instructor ') == 'instructor'
    assert normalize_organization_role('superadmin') is None


def test_global_admin_has_explicit_break_glass_access():
    db = _Db(SimpleNamespace(id=1, enabled=True))
    assert require_organization_access(db, _user('Admin'), 1, 'owner') is None


def test_membership_role_must_meet_minimum():
    membership = SimpleNamespace(role='student', is_active=True)
    db = _Db(SimpleNamespace(id=1, enabled=True), membership)
    with pytest.raises(HTTPException) as exc:
        require_organization_access(db, _user('Teacher'), 1, 'instructor')
    assert exc.value.status_code == 403


def test_unknown_membership_role_fails_closed():
    membership = SimpleNamespace(role='superadmin', is_active=True)
    db = _Db(SimpleNamespace(id=1, enabled=True), membership)
    with pytest.raises(HTTPException) as exc:
        require_organization_access(db, _user('Teacher'), 1)
    assert exc.value.status_code == 403
