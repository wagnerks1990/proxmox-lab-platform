from fastapi import Depends, HTTPException
from app.models.models import User
from app.api.deps import get_current_user


def normalize_role_name(user: User) -> str:
    role = getattr(getattr(user, 'role_rel', None), 'name', None) or getattr(user, 'role', None) or ''
    return role.strip().lower()


def is_admin(user: User) -> bool:
    return normalize_role_name(user) == 'admin' or getattr(user, 'role_id', None) == 3


def is_teacher(user: User) -> bool:
    return normalize_role_name(user) == 'teacher' or getattr(user, 'role_id', None) == 2


def is_admin_or_teacher(user: User) -> bool:
    return is_admin(user) or is_teacher(user)


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not is_admin(user):
        raise HTTPException(status_code=403, detail='Admin required')
    return user


def require_admin_or_teacher(user: User = Depends(get_current_user)) -> User:
    if not is_admin_or_teacher(user):
        raise HTTPException(status_code=403, detail='Teacher/Admin required')
    return user
