"""
User schemas for API validation
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=6, max_length=128, description="Password")

    @validator('username')
    def validate_username(cls, v):
        """验证用户名格式"""
        if not v.isalnum() and '_' not in v:
            raise ValueError('Username must contain only letters, numbers, and underscores')
        return v


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str
    password: str


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    email: str
    is_active: bool = True
    is_superuser: bool = False
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True  # Pydantic v2用from_attributes替代orm_mode


class UserUpdate(BaseModel):
    """用户更新请求"""
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class PasswordChange(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=128)


class Token(BaseModel):
    """JWT Token响应"""
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None
