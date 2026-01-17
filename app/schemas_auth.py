from pydantic import BaseModel
from typing import Optional


class UserBase(BaseModel):
    email: str
    name: Optional[str] = None


class UserProfileOut(BaseModel):
    show_quick_start: bool = True

    class Config:
        from_attributes = True


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: str
    is_active: bool = True
    is_superuser: bool = False
    profile: Optional[UserProfileOut] = None

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    show_quick_start: Optional[bool] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
