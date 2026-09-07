from __future__ import annotations


ROLE_STUDENT = 'Student'
ROLE_TEACHER = 'Teacher'
ROLE_ADMIN = 'Admin'
KNOWN_ROLES = frozenset({ROLE_STUDENT, ROLE_TEACHER, ROLE_ADMIN})
STAFF_ROLES = frozenset({ROLE_TEACHER, ROLE_ADMIN})


def get_role_name(user) -> str:
    """Return a canonical role name, preferring the role relationship.

    ``User.role`` is a deprecated compatibility column.  It must never
    override the role selected through ``role_id``/``role_rel`` because that
    would allow stale role strings to preserve privileges after a role change.
    """
    relationship = getattr(user, 'role_rel', None)
    relationship_name = getattr(relationship, 'name', None)
    if relationship_name in KNOWN_ROLES:
        return relationship_name

    legacy = getattr(user, 'role', None)
    if legacy in KNOWN_ROLES:
        return legacy
    legacy_name = getattr(legacy, 'name', None)
    if legacy_name in KNOWN_ROLES:
        return legacy_name

    fallback = getattr(user, 'role_name', None)
    if fallback in KNOWN_ROLES:
        return fallback
    return ''


def is_known_role(user) -> bool:
    return get_role_name(user) in KNOWN_ROLES


def can_manage_all_vms(user) -> bool:
    return get_role_name(user) in STAFF_ROLES
