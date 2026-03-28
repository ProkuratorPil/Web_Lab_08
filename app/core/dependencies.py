"""
Dependencies для аутентификации и авторизации.
"""
from fastapi import Depends, HTTPException, status, Cookie, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.core.jwt import verify_access, verify_refresh
from app.core.security import verify_token
from app.models.user import User
from app.models.token import Token, TokenType
from app.crud.token_crud import get_token_by_hash
from app.core.security import hash_token


# Schemes для извлечения токена
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    access_token: Optional[str] = Cookie(default=None, alias="access_token"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """
    Dependency для получения текущего авторизованного пользователя.
    Проверяет Access Token из Cookie или заголовка Authorization.
    """
    token = None
    
    # Пробуем получить из Cookie
    if access_token:
        token = access_token
    # Пробуем получить из заголовка Authorization
    elif credentials:
        token = credentials.credentials
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Валидируем JWT
    user_id = verify_access(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или истёкший токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Проверяем, что токен не отозван в БД
    token_hash = hash_token(token)
    db_token = get_token_by_hash(db, token_hash)
    if db_token and db_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен был отозван",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Получаем пользователя
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None),
        User.is_active == True
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
    access_token: Optional[str] = Cookie(default=None, alias="access_token"),
) -> Optional[User]:
    """
    Optional версия - возвращает пользователя или None.
    Используется для эндпоинтов, доступных всем.
    """
    if not access_token:
        return None
    
    try:
        user_id = verify_access(access_token)
        if not user_id:
            return None
        
        user = db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None),
            User.is_active == True
        ).first()
        
        return user
    except Exception:
        return None


async def get_refresh_token(
    refresh_token: Optional[str] = Cookie(default=None, alias="refresh_token"),
) -> str:
    """
    Dependency для получения Refresh Token из Cookie.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh токен отсутствует",
        )
    return refresh_token


async def validate_refresh_token(
    request: Request,
    refresh_token: str = Depends(get_refresh_token),
    db: Session = Depends(get_db),
) -> tuple[User, str]:
    """
    Валидирует Refresh Token и возвращает пользователя.
    Проверяет отзыв токена в БД.
    """
    user_id = verify_refresh(refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или истёкший refresh токен",
        )
    
    # Проверяем токен в БД
    token_hash = hash_token(refresh_token)
    db_token = get_token_by_hash(db, token_hash)
    
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен не найден в системе",
        )
    
    if db_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен был отозван",
        )
    
    # Получаем пользователя
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None),
        User.is_active == True
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )
    
    return user, refresh_token


def get_client_ip(request: Request) -> str:
    """Получает IP адрес клиента."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Получает User-Agent клиента."""
    return request.headers.get("User-Agent", "unknown")
