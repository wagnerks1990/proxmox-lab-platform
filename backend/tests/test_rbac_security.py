import pytest

from app.architecture.policies import PolicyError, can_launch_vm
from app.services.rbac import ROLE_ADMIN, ROLE_STUDENT, get_role_name


class Role:
    def __init__(self, name):
        self.name = name


class User:
    def __init__(self, user_id, *, relationship=None, legacy=None):
        self.id = user_id
        self.role_rel = relationship
        self.role = legacy


class VM:
    def __init__(self, owner_id):
        self.owner_id = owner_id


def test_relationship_role_wins_over_stale_legacy_admin():
    user = User(10, relationship=Role(ROLE_STUDENT), legacy=ROLE_ADMIN)
    assert get_role_name(user) == ROLE_STUDENT


def test_unknown_role_does_not_receive_student_owner_access():
    user = User(10, relationship=None, legacy="")
    with pytest.raises(PolicyError):
        can_launch_vm(user, VM(owner_id=10))


def test_student_can_launch_only_owned_vm():
    user = User(10, relationship=Role(ROLE_STUDENT))
    can_launch_vm(user, VM(owner_id=10))
    with pytest.raises(PolicyError):
        can_launch_vm(user, VM(owner_id=11))
