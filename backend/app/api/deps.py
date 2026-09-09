from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import InvalidTokenError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services.rbac import get_role_name
from app.db.session import get_db
from app.models.models import AuthSession, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_request_token(
    request: Request, bearer_token: str | None = Depends(oauth2_scheme)
) -> str:
    token = bearer_token or request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return token


def get_authenticated_user(
    token: str = Depends(get_request_token), db: Session = Depends(get_db)
) -> User:
    return get_user_from_token(token, db)


def get_current_user(user: User = Depends(get_authenticated_user)) -> User:
    if getattr(user, "force_password_change", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Password change required"
        )
    return user


def require_role(*roles):
    def checker(user: User = Depends(get_current_user)):
        if get_role_name(user) not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return checker


def get_user_from_token(token: str, db: Session) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except InvalidTokenError:
        raise credentials_exception

    username = payload.get("sub")
    token_id = payload.get("jti")
    token_version = payload.get("ver")
    if not username or not token_id or payload.get("typ") != "access":
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise credentials_exception
    if hasattr(user, "is_active") and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
        )
    if token_version != (getattr(user, "token_version", None) or 1):
        raise credentials_exception
    session = (
        db.query(AuthSession)
        .filter(AuthSession.token_id == token_id, AuthSession.user_id == user.id)
        .first()
    )
    if not session or session.revoked_at is not None:
        raise credentials_exception
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if session.expires_at and session.expires_at <= now:
        raise credentials_exception
    return user


def get_current_auth_session(
    token: str = Depends(get_request_token), db: Session = Depends(get_db)
) -> AuthSession:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except InvalidTokenError:
        raise credentials_exception
    user = get_user_from_token(token, db)
    session = (
        db.query(AuthSession)
        .filter(
            AuthSession.token_id == payload.get("jti"), AuthSession.user_id == user.id
        )
        .first()
    )
    if not session:
        raise credentials_exception
    return session
