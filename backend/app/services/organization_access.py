from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import Organization, OrganizationMembership, User
from app.services.rbac import ROLE_ADMIN, get_role_name


ORGANIZATION_ROLES = ('student', 'instructor', 'admin', 'owner')
ROLE_RANK = {name: rank for rank, name in enumerate(ORGANIZATION_ROLES)}


def normalize_organization_role(value: str | None) -> str | None:
    role = (value or '').strip().lower()
    return role if role in ROLE_RANK else None


def get_active_membership(db: Session, user_id: int, organization_id: int):
    return (
        db.query(OrganizationMembership)
        .filter(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.is_active.is_(True),
        )
        .first()
    )


def require_organization_access(
    db: Session,
    user: User,
    organization_id: int,
    minimum_role: str = 'student',
) -> OrganizationMembership | None:
    """Authorize tenant access; a global Admin is the explicit break-glass scope."""
    minimum = normalize_organization_role(minimum_role)
    if minimum is None:
        raise ValueError(f'Unknown minimum organization role: {minimum_role}')

    organization = db.query(Organization).filter(
        Organization.id == organization_id,
        Organization.enabled.is_(True),
    ).first()
    if not organization:
        raise HTTPException(status_code=404, detail='Organization not found')

    if get_role_name(user) == ROLE_ADMIN:
        return None

    membership = get_active_membership(db, user.id, organization_id)
    role = normalize_organization_role(getattr(membership, 'role', None))
    if membership is None or role is None or ROLE_RANK[role] < ROLE_RANK[minimum]:
        raise HTTPException(status_code=403, detail='Organization access denied')
    return membership
