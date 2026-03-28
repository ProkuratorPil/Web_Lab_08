# app/api/routers/user_router.py (или app/api/endpoints/users.py, в зависимости от вашей структуры)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.services.user_service import UserService # <- Предполагаемый сервис для User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, PaginationParams, PaginatedResponse # <- Предполагаемые схемы для User

# Изменили префикс и теги с "books" на "users"
router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    service = UserService(db)
    user = service.create(user_data) # <- Вызов метода сервиса для User
    return user

@router.get("/", response_model=PaginatedResponse)
def get_users(pagination: PaginationParams = Depends(), db: Session = Depends(get_db)):
    service = UserService(db)
    users, total = service.get_all_active(pagination) # <- Вызов метода сервиса для User
    total_pages = (total + pagination.limit - 1) // pagination.limit
    return {
        "data": users, # <- Возвращаем пользователей
        "meta": {
            "total": total,
            "page": pagination.page,
            "limit": pagination.limit,
            "totalPages": total_pages,
        }
    }

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    service = UserService(db)
    user = service.get_by_id(user_id) # <- Вызов метода сервиса для User
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") # <- Сообщение об ошибке
    return user

@router.put("/{user_id}", response_model=UserResponse)
def update_user_full(user_id: UUID, user_data: UserUpdate, db: Session = Depends(get_db)):
    service = UserService(db)
    user_response = service.update(user_id, user_data, partial=False) # <-- Получаем UserResponse или None
    if not user_response: # <-- Проверка на None
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_response # <-- Возврат Pydantic-модели

@router.patch("/{user_id}", response_model=UserResponse)
def update_user_partial(user_id: UUID, user_data: UserUpdate, db: Session = Depends(get_db)):
    service = UserService(db)
    user_response = service.update(user_id, user_data, partial=True) # <-- Получаем UserResponse или None
    if not user_response: # <-- Проверка на None
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_response # <-- Возврат Pydantic-модели

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: UUID, db: Session = Depends(get_db)):
    service = UserService(db)
    deleted = service.delete(user_id) # <- Вызов метода сервиса для User
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") # <- Сообщение об ошибке
    return None