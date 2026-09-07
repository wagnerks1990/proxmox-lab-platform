from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.vm import TemplateResponse, TemplateCreateRequest, TemplateUpdateRequest
from app.services import template_service
from app.models.models import VMTemplate
from app.services.organization_access import OrganizationContext, get_current_organization

router = APIRouter()


@router.get('/templates', response_model=list[TemplateResponse])
def templates(user=Depends(get_current_user), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    return template_service.list_templates(db, user, organization.id)


@router.get('/admin/templates', response_model=list[TemplateResponse])
def admin_templates(_user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    return db.query(VMTemplate).filter(VMTemplate.organization_id == organization.id).all()


@router.post('/admin/templates', response_model=TemplateResponse)
def create_template(payload: TemplateCreateRequest, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    return template_service.create_template(db, payload, organization.id)


@router.patch('/admin/templates/{id}', response_model=TemplateResponse)
def patch_template(id: int, payload: TemplateUpdateRequest, _user=Depends(require_role('Teacher', 'Admin')), db: Session = Depends(get_db), organization: OrganizationContext = Depends(get_current_organization)):
    return template_service.patch_template(db, id, payload, organization.id)
