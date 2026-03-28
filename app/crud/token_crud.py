"""
CRUD операции для работы с токенами.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional
from app.models.token import Token, TokenType
from app.core.security import hash_token


def create_token(
    db: Session,
    user_id: UUID,
    token: str,
    token_type: TokenType,
    user_agent: str = None,
    ip_address: str = None,
    expires_at: datetime = None
) -> Token:
    """
    Создаёт новую запись токена в БД.
    Токен хешируется перед сохранением.
    """
    token_hash = hash_token(token)
    
    db_token = Token(
        user_id=user_id,
        token_type=token_type,
        token_hash=token_hash,
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=expires_at
    )
    
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    
    return db_token


def get_token_by_hash(db: Session, token_hash: str) -> Optional[Token]:
    """Получает токен по его хешу."""
    return db.query(Token).filter(Token.token_hash == token_hash).first()


def get_user_tokens(db: Session, user_id: UUID) -> list[Token]:
    """Получает все активные токены пользователя."""
    return db.query(Token).filter(
        and_(
            Token.user_id == user_id,
            Token.is_revoked == False,
            Token.expires_at > datetime.now(timezone.utc)
        )
    ).all()


def revoke_token(db: Session, token_id: UUID) -> bool:
    """Отзывает токен по ID."""
    token = db.query(Token).filter(Token.id == token_id).first()
    if token:
        token.is_revoked = True
        db.commit()
        return True
    return False


def revoke_all_user_tokens(db: Session, user_id: UUID) -> int:
    """Отзывает все токены пользователя."""
    result = db.query(Token).filter(
        and_(
            Token.user_id == user_id,
            Token.is_revoked == False
        )
    ).update({"is_revoked": True})
    db.commit()
    return result


def cleanup_expired_tokens(db: Session) -> int:
    """Удаляет просроченные токены из БД."""
    result = db.query(Token).filter(
        Token.expires_at < datetime.now(timezone.utc)
    ).delete()
    db.commit()
    return result
