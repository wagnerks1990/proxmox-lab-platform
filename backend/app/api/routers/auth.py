from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services.rbac import get_role_name
from app.db.session import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.api.deps import get_current_user
from app.services.auth_service import login_user

router = APIRouter()


@router.post('/auth/login', response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return TokenResponse(access_token=login_user(db, data.username, data.password))


@router.get('/auth/me', response_model=UserResponse)
def me(user=Depends(get_current_user)):
    return UserResponse(id=user.id, username=user.username, email=user.email, role=get_role_name(user))
