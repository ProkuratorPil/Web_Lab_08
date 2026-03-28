# app/services/user_service.py
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from uuid import UUID
from datetime import datetime
from typing import Optional, Tuple
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, PaginationParams # <-- Добавлен UserResponse
from passlib.context import CryptContext # <-- Импорт CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto") # <-- Создаем контекст

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: UserCreate) -> UserResponse: # <-- Изменили возвращаемый тип
        # Хэшируем пароль
        hashed_password = self.hash_password(data.password)
        # Подготовим данные для создания, заменив password на hashed_password
        user_dict = data.model_dump()
        user_dict['hashed_password'] = hashed_password
        # Удалим оригинальный password из словаря, так как модели он не нужен
        del user_dict['password']

        user = User(**user_dict) # <-- Передаем подготовленный словарь
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Создаем и возвращаем Pydantic-модель UserResponse
        return UserResponse.from_orm(user) # <-- Используем from_orm или конструктор Pydantic

    def hash_password(self, password: str) -> str: # <-- Метод для хэширования
        return pwd_context.hash(password)

    # ... остальные методы ...
    def get_by_id(self, user_id: UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        user = self.db.execute(stmt).scalar_one_or_none()
        print(f"DEBUG UserService.get_by_id: Searched for {user_id}, found: {user}") # <-- Добавлен лог
        return user

    def get_all_active(self, pagination: PaginationParams) -> Tuple[list[User], int]:
        offset = (pagination.page - 1) * pagination.limit
        count_stmt = select(func.count()).select_from(select(User).where(User.deleted_at.is_(None)).subquery())
        total = self.db.execute(count_stmt).scalar()

        stmt = select(User).where(User.deleted_at.is_(None)).order_by(User.created_at.desc()).offset(offset).limit(pagination.limit)
        users = self.db.execute(stmt).scalars().all()
        return users, total # type: ignore

    def update(self, user_id: UUID, data: UserUpdate, partial: bool = False) -> Optional[UserResponse]: # <-- Изменили возвращаемый тип
        user = self.get_by_id(user_id)
        if not user:
            print(f"DEBUG UserService.update: User with id {user_id} not found.")
            return None
        print(f"DEBUG UserService.update: Found user {user.id} before update.")

        update_data = data.model_dump(exclude_unset=partial)
        if 'password' in update_data and update_data['password'] is not None:
            update_data['hashed_password'] = self.hash_password(update_data.pop('password'))

        for key, value in update_data.items():
            setattr(user, key, value)
        user.updated_at = datetime.utcnow()

        self.db.commit()
        print(f"DEBUG UserService.update: Committed changes for user {user.id}.")
        self.db.refresh(user)
        print(f"DEBUG UserService.update: Refreshed user {user.id}. Hashed password: {getattr(user, 'hashed_password', 'NOT_SET')}")
        print(f"DEBUG UserService.update: About to return user object: {user}")

        # --- СОЗДАЕМ Pydantic-МОДЕЛЬ ВНУТРИ СЕССИИ ---
        user_response = UserResponse.from_orm(user)
        print(f"DEBUG UserService.update: Returning UserResponse: {user_response}") # <-- Добавьте лог
        return user_response
        # ---------------------------------------------

    def delete(self, user_id: UUID) -> bool:
        user = self.get_by_id(user_id)
        if not user:
            return False
        user.deleted_at = datetime.utcnow()
        self.db.commit()
        return True