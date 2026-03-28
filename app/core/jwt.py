"""
Модуль для работы с JWT токенами.
Генерирует и валидирует Access и Refresh токены.
"""
import jwt
from datetime import datetime, timedelta, timezone
from uuid import UUID
from typing import Optional
from app.core.config import settings


class JWTManager:
    """Менеджер для работы с JWT токенами."""
    
    def __init__(
        self,
        access_secret: str = None,
        refresh_secret: str = None,
        access_expires: str = None,
        refresh_expires: str = None
    ):
        self.access_secret = access_secret or settings.JWT_ACCESS_SECRET
        self.refresh_secret = refresh_secret or settings.JWT_REFRESH_SECRET
        self.access_expires_delta = self._parse_delta(access_expires or settings.JWT_ACCESS_EXPIRATION)
        self.refresh_expires_delta = self._parse_delta(refresh_expires or settings.JWT_REFRESH_EXPIRATION)
    
    @staticmethod
    def _parse_delta(delta_str: str) -> timedelta:
        """Парсит строку формата '15m', '7d', '1h' в timedelta."""
        units = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800
        }
        
        unit = delta_str[-1].lower()
        value = int(delta_str[:-1])
        
        if unit not in units:
            raise ValueError(f"Unknown time unit: {unit}")
        
        return timedelta(seconds=value * units[unit])
    
    def create_access_token(self, user_id: UUID) -> tuple[str, datetime]:
        """
        Создаёт Access JWT токен.
        
        Returns:
            Кортеж (токен, дата истечения)
        """
        expires_at = datetime.now(timezone.utc) + self.access_expires_delta
        
        payload = {
            "sub": str(user_id),
            "type": "access",
            "exp": expires_at,
            "iat": datetime.now(timezone.utc)
        }
        
        token = jwt.encode(payload, self.access_secret, algorithm="HS256")
        return token, expires_at
    
    def create_refresh_token(self, user_id: UUID) -> tuple[str, datetime]:
        """
        Создаёт Refresh JWT токен.
        
        Returns:
            Кортеж (токен, дата истечения)
        """
        expires_at = datetime.now(timezone.utc) + self.refresh_expires_delta
        
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "exp": expires_at,
            "iat": datetime.now(timezone.utc)
        }
        
        token = jwt.encode(payload, self.refresh_secret, algorithm="HS256")
        return token, expires_at
    
    def create_token_pair(self, user_id: UUID) -> dict:
        """
        Создаёт пару Access + Refresh токенов.
        
        Returns:
            Словарь с токенами и метаданными
        """
        access_token, access_exp = self.create_access_token(user_id)
        refresh_token, refresh_exp = self.create_refresh_token(user_id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "access_expires_at": access_exp.isoformat(),
            "refresh_expires_at": refresh_exp.isoformat()
        }
    
    def verify_access_token(self, token: str) -> Optional[dict]:
        """
        Валидирует Access токен.
        
        Returns:
            Payload токена или None если невалиден
        """
        try:
            payload = jwt.decode(
                token,
                self.access_secret,
                algorithms=["HS256"]
            )
            
            if payload.get("type") != "access":
                return None
            
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def verify_refresh_token(self, token: str) -> Optional[dict]:
        """
        Валидирует Refresh токен.
        
        Returns:
            Payload токена или None если невалиден
        """
        try:
            payload = jwt.decode(
                token,
                self.refresh_secret,
                algorithms=["HS256"]
            )
            
            if payload.get("type") != "refresh":
                return None
            
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def decode_token(self, token: str) -> Optional[dict]:
        """
        Декодирует токен без проверки типа (для отладки).
        """
        try:
            # Пробуем оба секрета
            for secret in [self.access_secret, self.refresh_secret]:
                try:
                    payload = jwt.decode(token, secret, algorithms=["HS256"])
                    return payload
                except jwt.InvalidTokenError:
                    continue
            return None
        except Exception:
            return None


# Глобальный экземпляр для удобства
jwt_manager = JWTManager()


def create_tokens(user_id: UUID) -> dict:
    """Создаёт пару токенов для пользователя."""
    return jwt_manager.create_token_pair(user_id)


def verify_access(token: str) -> Optional[UUID]:
    """Валидирует access токен и возвращает user_id."""
    payload = jwt_manager.verify_access_token(token)
    if payload:
        return UUID(payload["sub"])
    return None


def verify_refresh(token: str) -> Optional[UUID]:
    """Валидирует refresh токен и возвращает user_id."""
    payload = jwt_manager.verify_refresh_token(token)
    if payload:
        return UUID(payload["sub"])
    return None
