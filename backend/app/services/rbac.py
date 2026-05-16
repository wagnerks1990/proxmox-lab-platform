from __future__ import annotations


def get_role_name(user) -> str:
    role = getattr(user, 'role', None)
    if isinstance(role, str):
        return role
    name = getattr(role, 'name', None)
    if isinstance(name, str):
        return name
    fallback = getattr(user, 'role_name', None)
    if isinstance(fallback, str):
        return fallback
    return ''
