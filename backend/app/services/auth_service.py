from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.models import User
from app.services.security import verify_password, create_access_token


def login_user(db: Session, username: str, password: str) -> str:
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    return create_access_token(user.username)
