from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username for login and profile")
    email: EmailStr = Field(..., description="Valid email address")
    full_name: Optional[str] = Field(None, max_length=100, description="User's full name")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100, description="Secure password (minimum 6 characters)")


class UserLogin(BaseModel):
    username_or_email: str = Field(..., description="Username or Email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    username: Optional[str] = None


class HomeResponse(BaseModel):
    message: str
    user: UserResponse
    status: str = "success"
    server_time: datetime
