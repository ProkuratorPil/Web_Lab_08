"""
OAuth 2.0 провайдеры для аутентификации через социальные сети.
Реализован поток Authorization Code Grant.
"""
import httpx
import secrets
from abc import ABC, abstractmethod
from typing import Optional, Tuple
from urllib.parse import urlencode
from app.core.config import settings


class OAuthProvider(ABC):
    """Базовый класс для OAuth провайдера."""
    
    provider_name: str
    authorization_url: str
    token_url: str
    userinfo_url: str
    
    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Генерирует URL для редиректа пользователя."""
        pass
    
    @abstractmethod
    async def exchange_code_for_token(self, code: str) -> dict:
        """Обменивает authorization code на access token."""
        pass
    
    @abstractmethod
    async def get_user_info(self, access_token: str) -> dict:
        """Получает информацию о пользователе."""
        pass
    
    def generate_state(self) -> str:
        """Генерирует случайный state для CSRF защиты."""
        return secrets.token_urlsafe(32)
    
    def verify_state(self, state: str, stored_state: str) -> bool:
        """Проверяет state для защиты от CSRF."""
        return secrets.compare_digest(state, stored_state)


class YandexProvider(OAuthProvider):
    """OAuth провайдер для Яндекс."""
    
    provider_name = "yandex"
    authorization_url = "https://oauth.yandex.ru/authorize"
    token_url = "https://oauth.yandex.ru/token"
    userinfo_url = "https://login.yandex.ru/info"
    
    def __init__(self):
        self.client_id = settings.YANDEX_CLIENT_ID
        self.client_secret = settings.YANDEX_CLIENT_SECRET
        self.callback_url = settings.YANDEX_CALLBACK_URL
    
    def get_authorization_url(self, state: str) -> str:
        """Генерирует URL авторизации Яндекс."""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.callback_url,
            "state": state,
        }
        return f"{self.authorization_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> dict:
        """Обменивает code на access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_info(self, access_token: str) -> dict:
        """Получает данные пользователя Яндекс."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.userinfo_url,
                headers={"Authorization": f"OAuth {access_token}"}
            )
            response.raise_for_status()
            data = response.json()
            
            # Приводим к единому формату
            return {
                "provider": self.provider_name,
                "provider_user_id": str(data.get("id", "")),
                "email": data.get("default_email", ""),
                "username": data.get("login", ""),
                "first_name": data.get("first_name", ""),
                "last_name": data.get("last_name", ""),
            }


class VKProvider(OAuthProvider):
    """OAuth провайдер для VK."""
    
    provider_name = "vk"
    authorization_url = "https://oauth.vk.com/authorize"
    token_url = "https://oauth.vk.com/access_token"
    userinfo_url = "https://api.vk.com/method/users.get"
    
    def __init__(self):
        self.client_id = settings.VK_CLIENT_ID
        self.client_secret = settings.VK_CLIENT_SECRET
        self.callback_url = settings.VK_CALLBACK_URL
        self.api_version = "5.131"
    
    def get_authorization_url(self, state: str) -> str:
        """Генерирует URL авторизации VK."""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.callback_url,
            "state": state,
            "scope": "email",
        }
        return f"{self.authorization_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> dict:
        """Обменивает code на access token."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.token_url,
                params={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.callback_url,
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_info(self, access_token: str) -> dict:
        """Получает данные пользователя VK."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.userinfo_url,
                params={
                    "access_token": access_token,
                    "v": self.api_version,
                    "fields": "first_name,last_name,screen_name",
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # VK возвращает массив users
            user_data = data.get("response", [{}])[0] if data.get("response") else {}
            
            return {
                "provider": self.provider_name,
                "provider_user_id": str(user_data.get("id", "")),
                "email": user_data.get("email", ""),
                "username": user_data.get("screen_name", ""),
                "first_name": user_data.get("first_name", ""),
                "last_name": user_data.get("last_name", ""),
            }


class OAuthProviderFactory:
    """Фабрика для создания OAuth провайдеров."""
    
    _providers = {
        "yandex": YandexProvider,
        "vk": VKProvider,
    }
    
    @classmethod
    def get_provider(cls, provider_name: str) -> Optional[OAuthProvider]:
        """Возвращает экземпляр провайдера по имени."""
        provider_class = cls._providers.get(provider_name.lower())
        if provider_class:
            return provider_class()
        return None
    
    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Возвращает список доступных провайдеров."""
        return list(cls._providers.keys())


async def get_oauth_user_info(provider_name: str, code: str) -> Optional[dict]:
    """
    Универсальная функция для получения данных пользователя через OAuth.
    
    Args:
        provider_name: Название провайдера (yandex, vk)
        code: Authorization code от провайдера
    
    Returns:
        Словарь с данными пользователя или None при ошибке
    """
    provider = OAuthProviderFactory.get_provider(provider_name)
    if not provider:
        return None
    
    try:
        token_data = await provider.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        
        if not access_token:
            return None
        
        user_info = await provider.get_user_info(access_token)
        
        # Добавляем email из token_data если есть
        if "email" not in user_info and "email" in token_data:
            user_info["email"] = token_data["email"]
        
        return user_info
    except Exception as e:
        # Логируем ошибку, но не возвращаем технические детали клиенту
        print(f"OAuth error for {provider_name}: {str(e)}")
        return None
