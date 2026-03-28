# app/schemas/file.py
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

# Схема для создания новой записи файла (обычно используется внутренне после загрузки)
class FileCreate(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    stored_filename: str = Field(..., min_length=1, max_length=255)
    file_path: str = Field(..., min_length=1, max_length=500)
    file_size: int = Field(..., gt=0) # Должен быть больше 0
    mime_type: str = Field(..., min_length=1, max_length=100)
    user_id: UUID # ID пользователя, который загрузил файл

# Схема для обновления записи файла (редко используется, но может понадобиться)
class FileUpdate(BaseModel):
    filename: Optional[str] = Field(None, min_length=1, max_length=255)
    stored_filename: Optional[str] = Field(None, min_length=1, max_length=255)
    file_path: Optional[str] = Field(None, min_length=1, max_length=500)
    file_size: Optional[int] = Field(None, gt=0)
    mime_type: Optional[str] = Field(None, min_length=1, max_length=100)
    user_id: Optional[UUID] = None # Обычно не меняется

# Схема для ответа клиенту
class FileResponse(BaseModel):
    id: UUID
    filename: str
    stored_filename: str
    file_path: str
    file_size: int
    mime_type: str
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    # deleted_at не включаем в ответ для активных файлов

    model_config = ConfigDict(from_attributes=True)

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(10, ge=1, le=100)

# Общая схема для ответа с пагинацией (тип данных в 'data' меняется на FileResponse)
class PaginatedResponse(BaseModel):
    data: list[FileResponse]
    meta: dict