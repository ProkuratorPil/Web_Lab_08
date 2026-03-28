# app/api/routers/file_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.file_service import FileService
from app.schemas.file import FileCreate, FileUpdate, FileResponse, PaginationParams, PaginatedResponse

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
def create_file(
    file_data: FileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Защищённый эндпоинт
):
    """
    Создание записи о файле.
    Доступ: Private (только авторизованные)
    """
    # Проверяем, что пользователь создаёт файл для себя
    if str(file_data.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя создавать файлы для других пользователей"
        )
    
    service = FileService(db)
    file_entry = service.create(file_data)
    return file_entry


@router.get("/", response_model=PaginatedResponse)
def get_files(
    pagination: PaginationParams = Depends(),
    user_id_filter: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Защищённый эндпоинт
):
    """
    Получение списка файлов (пагинированный).
    Доступ: Private
    
    Пользователь видит только свои файлы.
    """
    # Обычные пользователи видят только свои файлы
    # Админы могли бы видеть все (добавить проверку роли)
    user_filter = current_user.id
    
    service = FileService(db)
    files, total, total_pages = service.get_all_active(
        pagination, 
        user_id_filter=user_filter
    )
    return {
        "data": files,
        "meta": {
            "total": total,
            "page": pagination.page,
            "limit": pagination.limit,
            "totalPages": total_pages,
        }
    }


@router.get("/{file_id}", response_model=FileResponse)
def get_file(
    file_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Защищённый эндпоинт
):
    """
    Получение файла по ID.
    Доступ: Private (только владелец)
    """
    service = FileService(db)
    file_entry = service.get_by_id(file_id)
    
    if not file_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    
    # Проверка владения
    if file_entry.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на просмотр этого файла"
        )
    
    return file_entry


@router.put("/{file_id}", response_model=FileResponse)
def update_file_full(
    file_id: UUID,
    file_data: FileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Защищённый эндпоинт
):
    """
    Полное обновление записи о файле.
    Доступ: Private (только владелец)
    """
    # Сначала проверяем владение
    service = FileService(db)
    existing = service.get_by_id(file_id)
    
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    
    if existing.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на редактирование этого файла"
        )
    
    file_entry = service.update(file_id, file_data)
    return file_entry


@router.patch("/{file_id}", response_model=FileResponse)
def update_file_partial(
    file_id: UUID,
    file_data: FileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Защищённый эндпоинт
):
    """
    Частичное обновление записи о файле.
    Доступ: Private (только владелец)
    """
    # Проверяем владение
    service = FileService(db)
    existing = service.get_by_id(file_id)
    
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    
    if existing.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на редактирование этого файла"
        )
    
    file_entry = service.update(file_id, file_data)
    return file_entry


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Защищённый эндпоинт
):
    """
    Удаление файла (Soft Delete).
    Доступ: Private (только владелец)
    """
    # Проверяем владение
    service = FileService(db)
    existing = service.get_by_id(file_id)
    
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    
    if existing.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на удаление этого файла"
        )
    
    deleted = service.delete(file_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    
    return None
