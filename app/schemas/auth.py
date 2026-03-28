"""
DTO (Data Transfer Objects) для аутентификации и авторизации.
"""
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional
import re


class UserRegister(BaseModel):
    """DTO для регистрации нового пользователя."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=8, max_length=72)
    phone: Optional[str] = Field(None, max_length=20)
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username может содержать только латинские буквы, цифры, _ и -')
        return v.lower()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not re.search(r'[a-z]', v):
            raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
        if not re.search(r'\d', v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = re.sub(r'[^\d+]', '', v)
            if len(cleaned) < 10:
                raise ValueError('Номер телефона должен содержать минимум 10 цифр')
            return cleaned
        return v


class UserLogin(BaseModel):
    """DTO для входа пользователя."""
    email: EmailStr = Field(...)
    password: str = Field(...)


class TokenResponse(BaseModel):
    """DTO для ответа с токенами."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_expires_at: datetime
    refresh_expires_at: datetime


class UserResponse(BaseModel):
    """DTO для ответа с данными пользователя."""
    id: UUID
    username: str
    email: str
    phone: Optional[str] = None
    is_verified: bool
    is_oauth_user: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserProfile(BaseModel):
    """Расширенный профиль пользователя для /whoami."""
    id: UUID
    username: str
    email: str
    phone: Optional[str] = None
    is_verified: bool
    is_oauth_user: bool
    created_at: datetime
    oauth_providers: list[str] = []
    
    model_config = ConfigDict(from_attributes=True)


class ForgotPasswordRequest(BaseModel):
    """DTO для запроса сброса пароля."""
    email: EmailStr = Field(...)


class ResetPasswordRequest(BaseModel):
    """DTO для установки нового пароля."""
    token: str = Field(...)
    new_password: str = Field(..., min_length=8, max_length=72)
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not re.search(r'[a-z]', v):
            raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
        if not re.search(r'\d', v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    detail: Optional[str] = None
