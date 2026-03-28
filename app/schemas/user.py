# app/schemas/user.py
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional


# Схема для создания нового пользователя
class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)  # Уникальное имя пользователя
    email: str = Field(..., min_length=1, max_length=100)  # Уникальный email
    password: str = Field(..., min_length=6, max_length=72)  # Пароль (до хэширования), ограничен 72 символами
    first_name: Optional[str] = Field(None, max_length=50)  # Имя (опционально)
    last_name: Optional[str] = Field(None, max_length=50)  # Фамилия (опционально)
    phone: Optional[str] = Field(None, max_length=20)  # Телефон (опционально)

# Схема для обновления существующего пользователя
# Все поля опциональны, чтобы поддерживать частичное обновление
class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=6, max_length=72)  # Новый пароль (до хэширования), ограничен 72 символами
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = Field(None)  # Возможность деактивировать аккаунт


# Схема для ответа клиенту (не включает пароль)
class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    is_oauth_user: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    # deleted_at не включаем в ответ для активных пользователей

    model_config = ConfigDict(from_attributes=True)  # Позволяет ORM-объекту (User) маппиться на эту схему

# Схема для параметров пагинации (остается без изменений)
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)  # По умолчанию первая страница
    limit: int = Field(10, ge=1, le=100)  # По умолчанию 10 элементов, максимум 100

# Общая схема для ответа с пагинацией (тип данных в 'data' меняется на UserResponse)
class PaginatedResponse(BaseModel):
    data: list[UserResponse]  # <-- Изменили тип данных здесь
    meta: dict
