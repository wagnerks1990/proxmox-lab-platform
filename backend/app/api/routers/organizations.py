from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import Organization, OrganizationMembership, User
from app.services.rbac import ROLE_ADMIN, get_role_name
from app.services.organization_access import OrganizationContext, require_organization_role


router = APIRouter()


@router.get('/organizations')
def my_organizations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if get_role_name(user) == ROLE_ADMIN:
        rows = db.query(Organization).filter(Organization.enabled.is_(True)).order_by(Organization.name.asc()).all()
        return [{'id': row.id, 'name': row.name, 'slug': row.slug, 'role': 'owner', 'break_glass': True} for row in rows]
    memberships = db.query(OrganizationMembership).join(
        Organization, Organization.id == OrganizationMembership.organization_id,
    ).filter(
        OrganizationMembership.user_id == user.id,
        OrganizationMembership.is_active.is_(True),
        Organization.enabled.is_(True),
    ).all()
    return [{'id': row.organization.id, 'name': row.organization.name, 'slug': row.organization.slug, 'role': row.role, 'break_glass': False} for row in memberships]


@router.get('/organization/members')
def organization_members(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    organization: OrganizationContext = Depends(require_organization_role('instructor')),
):
    memberships = db.query(OrganizationMembership).filter(
        OrganizationMembership.organization_id == organization.id,
        OrganizationMembership.is_active.is_(True),
    ).order_by(OrganizationMembership.id.asc()).all()
    users = {row.id: row for row in db.query(User).filter(User.id.in_([membership.user_id for membership in memberships])).all()} if memberships else {}
    return [{
        'user_id': membership.user_id,
        'username': users[membership.user_id].username if membership.user_id in users else None,
        'email': users[membership.user_id].email if membership.user_id in users else None,
        'role': membership.role,
    } for membership in memberships]
