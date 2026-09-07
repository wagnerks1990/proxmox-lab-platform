from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import Organization, OrganizationMembership, User
from app.services.rbac import ROLE_ADMIN, get_role_name


ORGANIZATION_ROLES = ('student', 'instructor', 'admin', 'owner')
ROLE_RANK = {name: rank for rank, name in enumerate(ORGANIZATION_ROLES)}


@dataclass(frozen=True)
class OrganizationContext:
    id: int
    slug: str
    role: str
    break_glass: bool = False


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


def resolve_organization_context(
    db: Session,
    user: User,
    requested_organization_id: int | None = None,
) -> OrganizationContext:
    role = get_role_name(user)
    if requested_organization_id is not None:
        organization = db.query(Organization).filter(
            Organization.id == requested_organization_id,
            Organization.enabled.is_(True),
        ).first()
        if organization is None:
            raise HTTPException(status_code=404, detail='Organization not found')
        if role == ROLE_ADMIN:
            return OrganizationContext(organization.id, organization.slug, 'owner', True)
        membership = get_active_membership(db, user.id, organization.id)
        member_role = normalize_organization_role(getattr(membership, 'role', None))
        if membership is None or member_role is None:
            raise HTTPException(status_code=403, detail='Organization access denied')
        return OrganizationContext(organization.id, organization.slug, member_role)

    memberships = db.query(OrganizationMembership).join(
        Organization, Organization.id == OrganizationMembership.organization_id,
    ).filter(
        OrganizationMembership.user_id == user.id,
        OrganizationMembership.is_active.is_(True),
        Organization.enabled.is_(True),
    ).all()
    valid = [m for m in memberships if normalize_organization_role(m.role)]
    if len(valid) == 1:
        membership = valid[0]
        organization = membership.organization
        return OrganizationContext(organization.id, organization.slug, normalize_organization_role(membership.role))
    if len(valid) > 1:
        raise HTTPException(status_code=400, detail='X-Organization-ID is required for users with multiple organizations')
    if role == ROLE_ADMIN:
        organization = db.query(Organization).filter(Organization.enabled.is_(True)).order_by(Organization.id.asc()).first()
        if organization:
            return OrganizationContext(organization.id, organization.slug, 'owner', True)
    raise HTTPException(status_code=403, detail='No active organization membership')


def get_current_organization(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_organization_id: int | None = Header(default=None, alias='X-Organization-ID'),
) -> OrganizationContext:
    return resolve_organization_context(db, user, x_organization_id)
