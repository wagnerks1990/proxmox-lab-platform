from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services.rbac import get_role_name
from app.db.session import get_db
from app.models.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/auth/login')


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    return get_user_from_token(token, db)


def require_role(*roles):
    def checker(user: User = Depends(get_current_user)):
        if get_role_name(user) not in roles:
            raise HTTPException(status_code=403, detail='Forbidden')
        return user
    return checker


def get_user_from_token(token: str, db: Session) -> User:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise credentials_exception

    username = payload.get('sub')
    if not username:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise credentials_exception
    if hasattr(user, 'is_active') and not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User account is disabled')
    return user
