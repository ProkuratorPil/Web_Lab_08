from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # Nullable для OAuth пользователей
    password_salt = Column(String, nullable=True)  # Уникальная соль для пароля
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    
    # OAuth провайдеры
    yandex_id = Column(String, unique=True, nullable=True)
    vk_id = Column(String, unique=True, nullable=True)
    
    # Статус аккаунта
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Связи
    files = relationship("UploadedFile", order_by="UploadedFile.created_at", back_populates="user")
    tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")
    
    @property
    def is_oauth_user(self) -> bool:
        """Проверяет, зарегистрирован ли пользователь через OAuth"""
        return self.hashed_password is None and (self.yandex_id is not None or self.vk_id is not None)
