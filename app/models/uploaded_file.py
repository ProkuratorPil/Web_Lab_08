# app/models/uploaded_file.py
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    filename = Column(String, nullable=False)         # Оригинальное имя файла
    stored_filename = Column(String, nullable=False)  # Имя файла на сервере
    file_path = Column(String, nullable=False)        # Путь к файлу на диске
    file_size = Column(Integer, nullable=False)       # Размер файла в байтах
    mime_type = Column(String, nullable=False)        # MIME-тип файла
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False) # Связь с пользователем
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Поле для Soft Delete

    # Связь ORM: позволяет получить пользователя, загрузившего файл через uploaded_file.user
    user = relationship("User", back_populates="files")
