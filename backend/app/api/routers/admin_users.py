from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.models import User, Role, Permission, VMTemplate, StudentVM, VMSession, AuditLog
from app.services.security import hash_password

router = APIRouter()


def _user_out(u: User, role_name: str | None = None):
    return {
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'display_name': u.display_name,
        'role_id': u.role_id,
        'role': role_name or getattr(getattr(u, 'role_rel', None), 'name', None) or u.role,
        'is_active': u.is_active,
        'force_password_change': u.force_password_change,
        'last_login_at': u.last_login_at.isoformat() if u.last_login_at else None,
        'created_at': u.created_at.isoformat() if u.created_at else None,
    }


@router.get('/admin/users')
def list_admin_users(q: str | None = None, role: str | None = None, is_active: bool | None = None, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    query = db.query(User)
    if q:
        like = f'%{q}%'
        query = query.filter((User.username.ilike(like)) | (User.email.ilike(like)) | (User.display_name.ilike(like)))
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    rows = query.order_by(User.id.asc()).all()
    roles = {r.id: r.name for r in db.query(Role).all()}
    if role:
        rows = [u for u in rows if (roles.get(u.role_id, '')).lower() == role.lower()]
    return [_user_out(u, roles.get(u.role_id)) for u in rows]


@router.post('/admin/users')
def create_admin_user(payload: dict, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    for f in ('username', 'email', 'password'):
        if not payload.get(f):
            raise HTTPException(status_code=422, detail=f'{f} is required')
    role_name = payload.get('role')
    role_id = payload.get('role_id')
    if not role_id and role_name:
        rr = db.query(Role).filter(Role.name.ilike(role_name)).first()
        role_id = rr.id if rr else None
    if not role_id:
        raise HTTPException(status_code=422, detail='role_id or role is required')
    if db.query(User).filter(User.username == payload['username']).first():
        raise HTTPException(status_code=409, detail='username already exists')
    if db.query(User).filter(User.email == payload['email']).first():
        raise HTTPException(status_code=409, detail='email already exists')
    u = User(
        username=payload['username'],
        email=payload['email'],
        password_hash=hash_password(payload['password']),
        role_id=role_id,
        display_name=payload.get('display_name'),
        is_active=payload.get('is_active', True),
        force_password_change=payload.get('force_password_change', False),
    )
    db.add(u); db.commit(); db.refresh(u)
    return _user_out(u)


@router.patch('/admin/users/{id}')
def patch_admin_user(id: int, payload: dict, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == id).first()
    if not u:
        raise HTTPException(status_code=404, detail='User not found')
    for k in ('username', 'email', 'display_name', 'is_active', 'force_password_change'):
        if k in payload:
            setattr(u, k, payload[k])
    if 'role_id' in payload:
        u.role_id = payload['role_id']
    db.commit(); db.refresh(u)
    return _user_out(u)


@router.patch('/admin/users/{id}/password')
def reset_user_password(id: int, payload: dict, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == id).first()
    if not u:
        raise HTTPException(status_code=404, detail='User not found')
    if not payload.get('password'):
        raise HTTPException(status_code=422, detail='password is required')
    u.password_hash = hash_password(payload['password'])
    u.force_password_change = payload.get('force_password_change', True)
    db.commit()
    return {'ok': True, 'message': 'Password updated.'}


@router.patch('/admin/users/{id}/activate')
def activate_user(id: int, payload: dict, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == id).first()
    if not u:
        raise HTTPException(status_code=404, detail='User not found')
    u.is_active = bool(payload.get('is_active', True))
    db.commit(); db.refresh(u)
    return _user_out(u)


@router.patch('/admin/users/{id}/role')
def change_user_role(id: int, payload: dict, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == id).first()
    if not u:
        raise HTTPException(status_code=404, detail='User not found')
    role_id = payload.get('role_id')
    if not role_id:
        raise HTTPException(status_code=422, detail='role_id is required')
    u.role_id = role_id
    db.commit(); db.refresh(u)
    return _user_out(u)


@router.delete('/admin/users/{id}')
def delete_admin_user(id: int, force: bool = False, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == id).first()
    if not u:
        raise HTTPException(status_code=404, detail='User not found')
    deps = {
        'vms': db.query(StudentVM).filter(StudentVM.owner_id == id).count(),
        'sessions': db.query(VMSession).filter(VMSession.user_id == id).count(),
        'audit_logs': db.query(AuditLog).filter(AuditLog.actor_id == id).count(),
    }
    if any(deps.values()) and not force:
        u.is_active = False
        db.commit()
        return {'ok': True, 'deleted': False, 'deactivated': True, 'message': 'User has dependencies; user was deactivated instead of deleted.', 'dependencies': deps}
    db.delete(u); db.commit()
    return {'ok': True, 'deleted': True}


@router.get('/admin/users/{id}/permissions')
def user_permissions(id: int, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    if not db.query(User).filter(User.id == id).first():
        raise HTTPException(status_code=404, detail='User not found')
    rows = db.query(Permission).filter(Permission.user_id == id).all()
    template_ids = [r.template_id for r in rows]
    templates = db.query(VMTemplate).filter(VMTemplate.id.in_(template_ids)).all() if template_ids else []
    return {'direct_template_ids': template_ids, 'templates': [{'id': t.id, 'name': t.name, 'source_vmid': t.source_vmid, 'proxmox_node': t.proxmox_node} for t in templates]}


@router.patch('/admin/users/{id}/permissions')
def patch_user_permissions(id: int, payload: dict, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    if not db.query(User).filter(User.id == id).first():
        raise HTTPException(status_code=404, detail='User not found')
    template_ids = [int(x) for x in (payload.get('template_ids') or [])]
    db.query(Permission).filter(Permission.user_id == id).delete()
    for tid in template_ids:
        db.add(Permission(user_id=id, template_id=tid))
    db.commit()
    return {'ok': True, 'template_ids': template_ids}


@router.get('/admin/users/{id}/activity')
def user_activity(id: int, _user=Depends(require_role('Admin')), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == id).first()
    if not u:
        raise HTTPException(status_code=404, detail='User not found')
    return {
        'user_id': id,
        'username': u.username,
        'vm_count': db.query(StudentVM).filter(StudentVM.owner_id == id).count(),
        'session_count': db.query(VMSession).filter(VMSession.user_id == id).count(),
        'audit_log_count': db.query(AuditLog).filter(AuditLog.actor_id == id).count(),
        'last_login_at': u.last_login_at.isoformat() if u.last_login_at else None,
    }
