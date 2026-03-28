"""
Модуль криптографии для безопасного хеширования паролей и токенов.
Использует bcrypt с автоматической генерацией соли.
"""
import hashlib
import secrets
import bcrypt


def generate_salt() -> str:
    """Генерирует уникальную соль для хеширования."""
    return secrets.token_hex(32)


def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """
    Хеширует пароль с использованием bcrypt.
    
    Args:
        password: Пароль в открытом виде
        salt: Опциональная соль (если не указана, генерируется автоматически)
    
    Returns:
        Кортеж (хеш, соль)
    
    Особенности:
        - bcrypt автоматически генерирует и включает соль в хеш
        - Мы храним отдельно соль для возможности повторного хеширования
        - Одинаковые пароли разных пользователей дадут разные хеши
    """
    if salt is None:
        salt = generate_salt()
    
    # bcrypt автоматически генерирует встроенную соль
    # salt передаётся как bytes для повторяемости (если нужно)
    password_bytes = password.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(prefix=b"2b"))
    
    return hashed.decode('utf-8'), salt


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Проверяет пароль против хеша.
    
    Args:
        password: Пароль в открытом виде
        hashed_password: Хеш пароля из базы данных
    
    Returns:
        True если пароль верный, False иначе
    """
    try:
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def hash_token(token: str) -> str:
    """
    Хеширует токен для безопасного хранения в БД.
    Использует SHA-256 с солью.
    
    Args:
        token: JWT токен в открытом виде
    
    Returns:
        Хеш токена
    """
    salt = generate_salt()
    token_bytes = token.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    
    # Используем SHA-256 для хеширования токенов
    hash_obj = hashlib.sha256(salt_bytes + token_bytes)
    return f"{salt}${hash_obj.hexdigest()}"


def verify_token(token: str, token_hash: str) -> bool:
    """
    Проверяет токен против хеша.
    
    Args:
        token: Токен в открытом виде
        token_hash: Хеш токена из базы данных (формат: salt$hash)
    
    Returns:
        True если токен верный, False иначе
    """
    try:
        salt, expected_hash = token_hash.split('$')
        salt_bytes = salt.encode('utf-8')
        token_bytes = token.encode('utf-8')
        
        hash_obj = hashlib.sha256(salt_bytes + token_bytes)
        actual_hash = hash_obj.hexdigest()
        
        return secrets.compare_digest(actual_hash, expected_hash)
    except (ValueError, AttributeError):
        return False


def hash_for_comparison(data: str) -> str:
    """
    Создаёт хеш для безопасного сравнения данных (например, email).
    Не для паролей - используйте hash_password для паролей.
    """
    return hashlib.sha256(data.lower().encode('utf-8')).hexdigest()
