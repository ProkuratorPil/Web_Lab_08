# app/services/file_service.py
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from uuid import UUID
from datetime import datetime
from typing import Optional, Tuple
from app.models.uploaded_file import UploadedFile
from app.schemas.file import FileCreate, FileUpdate, PaginationParams

class FileService:
    def __init__(self, db: Session):
        self.db = db

    def create(self,  FileCreate) -> UploadedFile: # <- Параметр 'data' теперь корректно объявлен
        # Импорт внутри метода, чтобы избежать циклических зависимостей на этапе загрузки модуля
        from app.crud.file_crud import create_file
        return create_file(self.db, data) # <- Используем 'data', который передан в метод

    def get_by_id(self, file_id: UUID) -> Optional[UploadedFile]:
        # Импорт внутри метода
        from app.crud.file_crud import get_file_by_id
        return get_file_by_id(self.db, file_id)

    def get_all_active(self, pagination: PaginationParams, user_id_filter: Optional[UUID] = None) -> Tuple[list[UploadedFile], int, int]:
        # Импорт внутри метода
        from app.crud.file_crud import get_files
        offset = (pagination.page - 1) * pagination.limit
        # get_files возвращает Tuple[list[UploadedFile], int] (files, total)
        files, total = get_files(self.db, user_id_filter=user_id_filter, skip=offset, limit=pagination.limit)
        total_pages = (total + pagination.limit - 1) // pagination.limit
        # Теперь возвращаем три значения: список файлов, общее количество, количество страниц
        return files, total, total_pages

    def update(self, file_id: UUID,  FileUpdate) -> Optional[UploadedFile]: # <- Параметр 'data' теперь корректно объявлен
        # Импорт внутри метода
        from app.crud.file_crud import update_file
        return update_file(self.db, file_id, data) # <- Используем 'data', который передан в метод

    def delete(self, file_id: UUID) -> bool:
        # Импорт внутри метода
        from app.crud.file_crud import soft_delete_file
        return soft_delete_file(self.db, file_id)