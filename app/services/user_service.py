# app/services/user_service.py
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from uuid import UUID
from datetime import datetime
from typing import Optional, Tuple
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, PaginationParams
from app.core.cache import cache_service
from app.core.config import settings
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: UserCreate) -> UserResponse:
        # Проверка уникальности username и email
        existing = self.db.query(User).filter(
            User.username == data.username,
            User.deleted_at.is_(None)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким username уже существует"
            )

        existing = self.db.query(User).filter(
            User.email == data.email,
            User.deleted_at.is_(None)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует"
            )

        hashed_password = self.hash_password(data.password)
        user_dict = data.model_dump()
        user_dict['hashed_password'] = hashed_password
        del user_dict['password']

        user = User(**user_dict)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        result = UserResponse.from_orm(user)
        # Инвалидация списков при создании
        cache_service.delete_by_pattern("wp:users:list:*")
        return result

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Внутренний метод без кеширования (для ORM-операций)."""
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        user = self.db.execute(stmt).scalar_one_or_none()
        return user

    def get_by_id_cached(self, user_id: UUID):
        """Публичный метод с кешированием (для API ответов)."""
        cache_key = f"wp:users:detail:{user_id}"
        cached = cache_service.get(cache_key)
        if cached:
            return cached

        user = self.get_by_id(user_id)
        if user:
            user_data = UserResponse.model_validate(user).model_dump(mode="json")
            cache_service.set(cache_key, user_data, ttl=settings.CACHE_TTL_DEFAULT)
            return user
        return None

    def get_all_active(self, pagination: PaginationParams) -> Tuple[list, int]:
        cache_key = f"wp:users:list:page:{pagination.page}:limit:{pagination.limit}"
        cached = cache_service.get(cache_key)
        if cached:
            return cached["users"], cached["total"]

        offset = (pagination.page - 1) * pagination.limit
        count_stmt = select(func.count()).select_from(select(User).where(User.deleted_at.is_(None)).subquery())
        total = self.db.execute(count_stmt).scalar()

        stmt = select(User).where(User.deleted_at.is_(None)).order_by(User.created_at.desc()).offset(offset).limit(pagination.limit)
        users = self.db.execute(stmt).scalars().all()

        # Кешируем сериализованные данные
        users_data = [UserResponse.model_validate(u).model_dump(mode="json") for u in users]
        cache_service.set(cache_key, {"users": users_data, "total": total}, ttl=settings.CACHE_TTL_DEFAULT)
        return users, total

    def update(self, user_id: UUID, data: UserUpdate, partial: bool = False) -> Optional[UserResponse]:
        user = self.get_by_id(user_id)
        if not user:
            return None

        update_data = data.model_dump(exclude_unset=partial)
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if 'password' in update_data and update_data['password'] is not None:
            update_data['hashed_password'] = self.hash_password(update_data.pop('password'))

        for key, value in update_data.items():
            setattr(user, key, value)
        user.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(user)

        user_response = UserResponse.from_orm(user)
        # Инвалидация кеша при обновлении
        cache_service.delete_by_pattern("wp:users:list:*")
        cache_service.delete(f"wp:users:detail:{user_id}")
        cache_service.delete(f"wp:users:profile:{user_id}")
        return user_response

    def delete(self, user_id: UUID) -> bool:
        user = self.get_by_id(user_id)
        if not user:
            return False
        user.deleted_at = datetime.utcnow()
        self.db.commit()
        # Инвалидация кеша при удалении
        cache_service.delete_by_pattern("wp:users:list:*")
        cache_service.delete(f"wp:users:detail:{user_id}")
        cache_service.delete(f"wp:users:profile:{user_id}")
        return True
