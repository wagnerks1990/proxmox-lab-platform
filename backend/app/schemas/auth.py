from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    role_id: int | None = None
    is_active: bool = True
