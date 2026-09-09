from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.organization_access import (
    ORGANIZATION_ROLES,
    OrganizationContext,
    enforce_organization_role,
    normalize_organization_role,
    organization_role_at_least,
    require_organization_access,
    resolve_organization_context,
)


class _Query:
    def __init__(self, result):
        self.result = result

    def filter(self, *_args):
        return self

    def first(self):
        return self.result

    def all(self):
        return self.result

    def join(self, *_args):
        return self

    def order_by(self, *_args):
        return self


class _Db:
    def __init__(self, organization, membership=None):
        self.results = [organization, membership]

    def query(self, _model):
        return _Query(self.results.pop(0))


def _user(role_name, user_id=7):
    return SimpleNamespace(
        id=user_id, role="Student", role_rel=SimpleNamespace(name=role_name)
    )


def test_organization_roles_are_explicit_and_normalized():
    assert ORGANIZATION_ROLES == ("student", "instructor", "admin", "owner")
    assert normalize_organization_role(" Instructor ") == "instructor"
    assert normalize_organization_role("superadmin") is None


def test_global_admin_has_explicit_break_glass_access():
    db = _Db(SimpleNamespace(id=1, enabled=True))
    assert require_organization_access(db, _user("Admin"), 1, "owner") is None


def test_membership_role_must_meet_minimum():
    membership = SimpleNamespace(role="student", is_active=True)
    db = _Db(SimpleNamespace(id=1, enabled=True), membership)
    with pytest.raises(HTTPException) as exc:
        require_organization_access(db, _user("Teacher"), 1, "instructor")
    assert exc.value.status_code == 403


def test_unknown_membership_role_fails_closed():
    membership = SimpleNamespace(role="superadmin", is_active=True)
    db = _Db(SimpleNamespace(id=1, enabled=True), membership)
    with pytest.raises(HTTPException) as exc:
        require_organization_access(db, _user("Teacher"), 1)
    assert exc.value.status_code == 403


def test_single_membership_is_selected_automatically():
    organization = SimpleNamespace(id=11, slug="engineering", enabled=True)
    membership = SimpleNamespace(
        role="instructor", is_active=True, organization=organization
    )
    db = _Db([membership])
    context = resolve_organization_context(db, _user("Teacher"), None)
    assert (context.id, context.slug, context.role, context.break_glass) == (
        11,
        "engineering",
        "instructor",
        False,
    )


def test_multiple_memberships_require_explicit_header():
    organizations = [
        SimpleNamespace(id=1, slug="one"),
        SimpleNamespace(id=2, slug="two"),
    ]
    memberships = [
        SimpleNamespace(role="student", organization=organization)
        for organization in organizations
    ]
    db = _Db(memberships)
    with pytest.raises(HTTPException) as exc:
        resolve_organization_context(db, _user("Student"), None)
    assert exc.value.status_code == 400
    assert "X-Organization-ID" in exc.value.detail


def test_requested_organization_denies_non_member():
    db = _Db(SimpleNamespace(id=9, slug="private", enabled=True), None)
    with pytest.raises(HTTPException) as exc:
        resolve_organization_context(db, _user("Student"), 9)
    assert exc.value.status_code == 403


def test_requested_organization_allows_admin_break_glass():
    db = _Db(SimpleNamespace(id=9, slug="private", enabled=True))
    context = resolve_organization_context(db, _user("Admin"), 9)
    assert context.break_glass is True
    assert context.role == "owner"


@pytest.mark.parametrize(
    ("role", "minimum", "allowed"),
    [
        ("student", "student", True),
        ("student", "instructor", False),
        ("instructor", "instructor", True),
        ("instructor", "admin", False),
        ("admin", "instructor", True),
        ("admin", "admin", True),
        ("admin", "owner", False),
        ("owner", "student", True),
        ("owner", "owner", True),
    ],
)
def test_organization_role_matrix(role, minimum, allowed):
    context = OrganizationContext(1, "test", role)
    assert organization_role_at_least(context, minimum) is allowed
    if allowed:
        assert enforce_organization_role(context, minimum) is context
    else:
        with pytest.raises(HTTPException) as exc:
            enforce_organization_role(context, minimum)
        assert exc.value.status_code == 403
