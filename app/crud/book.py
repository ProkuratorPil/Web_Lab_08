from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from typing import Optional, Tuple

# Функция для получения списка пользователей с пагинацией
def get_users(db: Session, skip: int = 0, limit: int = 10) -> Tuple[list[User], int]:
    query = db.query(User).filter(User.deleted_at.is_(None)) # <- Фильтруем по User
    total = query.count()
    users = query.offset(skip).limit(limit).all() # <- Получаем пользователей
    return users, total

# Функция для получения пользователя по ID
def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
    return db.query(User).filter( # <- Запрашиваем User
        User.id == user_id,
        User.deleted_at.is_(None)
    ).first()

# Функция для создания нового пользователя
def create_user(db: Session, user_in: UserCreate) -> User:
    db_user = User(**user_in.model_dump()) # <- Создаем экземпляр User
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Функция для обновления пользователя
def update_user(db: Session, user_id: UUID, user_update: UserUpdate) -> Optional[User]:
    db_user = get_user_by_id(db, user_id) # <- Вызываем функцию для User
    if not db_user:
        return None
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    db.commit()
    db.refresh(db_user)
    return db_user

# Функция для мягкого удаления пользователя
def soft_delete_user(db: Session, user_id: UUID) -> bool:
    # Захватываем пользователя по ID, включая возможно удаленных (без фильтра deleted_at)
    # Это позволяет попытаться "удалить" уже удаленного пользователя (хотя обычно возвращают False или игнорируют).
    # В данном случае, мы проверим, что он не удален, перед тем как удалять.
    db_user = db.query(User).filter(User.id == user_id).first() # <- Запрашиваем User
    if db_user and db_user.deleted_at is None: # <- Проверяем, что запись существует и не удалена
        db_user.deleted_at = func.now() # <- Устанавливаем время удаления
        db.commit()
        return True
    return False
