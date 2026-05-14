"""
Async router for authentication and authorization with MongoDB.
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Optional
import secrets
import uuid

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.core.jwt import create_tokens, jwt_manager, verify_refresh
from app.core.security import hash_password, verify_password, hash_token
from app.core.dependencies import (
    get_current_user,
    validate_refresh_token,
    get_client_ip,
    get_user_agent
)
from app.core.cache import cache_service
from app.core.oauth.providers import OAuthProviderFactory, get_oauth_user_info
from app.common.queue.rabbitmq_service import rabbitmq_service
from app.services.email_service import email_service
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    UserProfile,
    TokenResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse
)
from app.schemas.common import get_auth_responses
from app.models.user import UserDocument
from app.models.token import TokenType, TokenDocument
from app.crud.token_crud import create_token, revoke_token, revoke_all_user_tokens, get_token_by_hash


router = APIRouter(prefix="/auth", tags=["Auth"])


oauth_states = {}


def set_auth_cookies(response, access_token, refresh_token, access_expires, refresh_expires):
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="lax", max_age=900)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="lax", max_age=604800)


def clear_auth_cookies(response):
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")


def get_oauth_providers_list(user: UserDocument) -> list[str]:
    providers = []
    if user.yandex_id:
        providers.append("yandex")
    if user.vk_id:
        providers.append("vk")
    return providers


async def _save_tokens(user_id, tokens: dict, ip: str, ua: str):
    """Save tokens to MongoDB and JTI Access token to Redis."""
    access_jti = tokens.get("access_jti")
    access_ttl = int(jwt_manager.access_expires_delta.total_seconds())

    # Save JTI to Redis for instant revocation
    if access_jti:
        redis_key = f"wp:auth:user:{user_id}:access:{access_jti}"
        cache_service.set(redis_key, "valid", ttl=access_ttl)

    await create_token(
        user_id=user_id,
        token=tokens["access_token"],
        token_type=TokenType.access,
        user_agent=ua,
        ip_address=ip,
        expires_at=datetime.now(timezone.utc) + jwt_manager.access_expires_delta
    )
    await create_token(
        user_id=user_id,
        token=tokens["refresh_token"],
        token_type=TokenType.refresh,
        user_agent=ua,
        ip_address=ip,
        expires_at=datetime.now(timezone.utc) + jwt_manager.refresh_expires_delta
    )


def _invalidate_user_session_cache(user_id):
    """Invalidate user session and profile cache."""
    cache_service.delete_by_pattern(f"wp:auth:user:{user_id}:access:*")
    cache_service.delete(f"wp:users:profile:{user_id}")


async def _publish_user_registered_event(user_id: str, email: str, display_name: str) -> None:
    """
    Публикует событие регистрации пользователя в RabbitMQ.
    Выполняется асинхронно, ошибки не прерывают регистрацию.
    """
    try:
        event_payload = {
            "eventId": str(uuid.uuid4()),
            "eventType": "user.registered",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "userId": str(user_id),
                "email": email,
                "displayName": display_name,
            },
            "metadata": {
                "attempt": 1,
                "sourceService": "auth-service",
            },
        }

        await rabbitmq_service.publish(
            exchange="app.events",
            routing_key="user.registered",
            payload=event_payload,
            persistent=True,
        )
        logger.info(f"User registered event published for user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to publish user registered event: {e}")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="Создаёт нового пользователя с указанными данными. Возвращает данные созданного пользователя без токенов.",
    response_description="Данные созданного пользователя",
    responses={
        **get_auth_responses(400, 422),
    }
)
async def register(user_data: UserRegister):
    existing = await UserDocument.find_one(UserDocument.email == user_data.email, UserDocument.deleted_at == None)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь с таким email уже существует")

    existing = await UserDocument.find_one(UserDocument.username == user_data.username.lower())
    if existing and existing.deleted_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь с таким username уже существует")

    hashed_pwd, salt = hash_password(user_data.password)

    user = UserDocument(
        username=user_data.username.lower(),
        email=user_data.email.lower(),
        hashed_password=hashed_pwd,
        password_salt=salt,
        phone=user_data.phone,
        is_verified=False,
    )

    await user.insert()

    # Публикация события регистрации в RabbitMQ для асинхронной отправки email
    display_name = user_data.email.split("@")[0]  # Fallback display name
    await _publish_user_registered_event(
        user_id=str(user.id),
        email=user.email,
        display_name=display_name,
    )

    return UserResponse(
        id=user.id, username=user.username, email=user.email, phone=user.phone,
        is_verified=user.is_verified, is_oauth_user=False, created_at=user.created_at
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Авторизация пользователя",
    description="Авторизует пользователя по email и паролю. Устанавливает HttpOnly cookies с токенами.",
    response_description="JWT токены доступа и обновления",
    responses={
        **get_auth_responses(400, 401, 422),
    }
)
async def login(response: Response, request: Request, user_data: UserLogin):
    user = await UserDocument.find_one(UserDocument.email == user_data.email.lower(), UserDocument.deleted_at == None)

    if not user or not user.hashed_password or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Аккаунт деактивирован")

    tokens = create_tokens(user.id)
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    await _save_tokens(user.id, tokens, ip, ua)

    set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"], tokens["access_expires_at"], tokens["refresh_expires_at"])
    response_data = {k: v for k, v in tokens.items() if k != "access_jti"}
    return TokenResponse(**response_data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Обновление токенов",
    description="Обновляет access и refresh токены по действующему refresh токену из cookie.",
    response_description="Новая пара JWT токенов",
    responses={
        **get_auth_responses(401),
    }
)
async def refresh_tokens(response: Response, request: Request, result: tuple = Depends(validate_refresh_token)):
    user, old_refresh_token = result
    old_token_hash_val = hash_token(old_refresh_token)
    tokens = create_tokens(user.id)
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    await _save_tokens(user.id, tokens, ip, ua)

    old_token = await get_token_by_hash(old_token_hash_val)
    if old_token:
        old_token.is_revoked = True
        await old_token.save()

    set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"], tokens["access_expires_at"], tokens["refresh_expires_at"])
    response_data = {k: v for k, v in tokens.items() if k != "access_jti"}
    return TokenResponse(**response_data)


@router.get(
    "/whoami",
    response_model=UserProfile,
    summary="Информация о текущем пользователе",
    description="Возвращает профиль авторизованного пользователя. Использует кеш Redis.",
    response_description="Данные профиля пользователя",
    responses={
        **get_auth_responses(401),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
async def whoami(current_user: UserDocument = Depends(get_current_user)):
    cache_key = f"wp:users:profile:{current_user.id}"
    cached = cache_service.get(cache_key)
    if cached:
        return UserProfile(**cached)

    profile = UserProfile(
        id=current_user.id, username=current_user.username, email=current_user.email, phone=current_user.phone,
        is_verified=current_user.is_verified, is_oauth_user=current_user.is_oauth_user,
        created_at=current_user.created_at, oauth_providers=get_oauth_providers_list(current_user)
    )
    cache_service.set(cache_key, profile.model_dump(mode="json"), ttl=settings.CACHE_TTL_DEFAULT)
    return profile


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Выход из системы",
    description="Завершает текущую сессию: отзывает refresh токен, удаляет JTI из Redis и очищает cookies.",
    response_description="Подтверждение выхода",
    responses={
        **get_auth_responses(401),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
async def logout(response: Response, request: Request, current_user: UserDocument = Depends(get_current_user)):
    # Invalidate JTI Access token in Redis
    access_token = request.cookies.get("access_token")
    if access_token:
        payload = jwt_manager.decode_token(access_token)
        if payload and payload.get("jti"):
            jti = payload["jti"]
            cache_service.delete(f"wp:auth:user:{current_user.id}:access:{jti}")

    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        token_hash_val = hash_token(refresh_token)
        token = await get_token_by_hash(token_hash_val)
        if token and token.user_id == current_user.id:
            token.is_revoked = True
            await token.save()

    # Invalidate profile cache
    cache_service.delete(f"wp:users:profile:{current_user.id}")
    clear_auth_cookies(response)
    return MessageResponse(message="Сессия завершена")


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    summary="Выход из всех сессий",
    description="Отзывает все токены пользователя, удаляет все JTI из Redis и очищает cookies.",
    response_description="Подтверждение отзыва всех сессий",
    responses={
        **get_auth_responses(401),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
async def logout_all(response: Response, current_user: UserDocument = Depends(get_current_user)):
    count = await revoke_all_user_tokens(current_user.id)
    # Remove all user JTI from Redis
    cache_service.delete_by_pattern(f"wp:auth:user:{current_user.id}:access:*")
    # Invalidate profile cache
    cache_service.delete(f"wp:users:profile:{current_user.id}")
    clear_auth_cookies(response)
    return MessageResponse(message="Все сессии завершены", detail=f"Отозвано токенов: {count}")


@router.get(
    "/oauth/{provider}",
    summary="Инициализация OAuth авторизации",
    description="Перенаправляет пользователя на страницу авторизации выбранного OAuth провайдера (yandex или vk).",
    response_description="Редирект на страницу авторизации провайдера",
    responses={
        **get_auth_responses(400),
    }
)
async def oauth_init(provider: str):
    provider_name = provider.lower()
    oauth_provider = OAuthProviderFactory.get_provider(provider_name)
    if not oauth_provider:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Провайдер '{provider}' не поддерживается")
    state = oauth_provider.generate_state()
    oauth_states[state] = provider_name
    return RedirectResponse(url=oauth_provider.get_authorization_url(state))


@router.get(
    "/oauth/{provider}/callback",
    summary="Callback OAuth авторизации",
    description="Обрабатывает ответ от OAuth провайдера после успешной авторизации. Создаёт или обновляет пользователя и устанавливает токены в cookies.",
    response_description="Редирект на главную страницу",
    responses={
        **get_auth_responses(400),
    }
)
async def oauth_callback(
    provider: str,
    code: Optional[str] = None,
    state: Optional[str] = None,
    response: Response = None,
    request: Request = None,
):
    provider_name = provider.lower()
    if not code or not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Отсутствуют обязательные параметры code и state")
    if state not in oauth_states or oauth_states[state] != provider_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный state")
    del oauth_states[state]
    user_info = await get_oauth_user_info(provider_name, code)
    if not user_info:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не удалось получить данные от провайдера")
    provider_user_id = user_info.get("provider_user_id")
    provider_id_field = f"{provider_name}_id"
    
    user = await UserDocument.find_one({provider_id_field: provider_user_id, "deleted_at": None})
    if not user:
        email = user_info.get("email")
        if email:
            user = await UserDocument.find_one(UserDocument.email == email.lower(), UserDocument.deleted_at == None)
        if user:
            setattr(user, provider_id_field, provider_user_id)
            if not user.is_verified:
                user.is_verified = True
        else:
            username = user_info.get("username") or f"{provider_name}_{provider_user_id}"
            user_data = {
                "username": username.lower(),
                "email": (email or f"{provider_user_id}@{provider_name}.oauth").lower(),
                "is_verified": True,
                provider_id_field: provider_user_id
            }
            user = UserDocument(**user_data)
            await user.insert()
    else:
        await user.save()
    
    tokens = create_tokens(user.id)
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    await _save_tokens(user.id, tokens, ip, ua)
    set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"], tokens["access_expires_at"], tokens["refresh_expires_at"])
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Запрос сброса пароля",
    description="Отправляет инструкцию по сбросу пароля на указанный email (заглушка).",
    response_description="Подтверждение отправки",
    responses={
        **get_auth_responses(422),
    }
)
async def forgot_password(data: ForgotPasswordRequest):
    return MessageResponse(message="Если аккаунт существует, на email отправлена инструкция по сбросу пароля")


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Сброс пароля",
    description="Устанавливает новый пароль по токену сброса (заглушка).",
    response_description="Подтверждение изменения пароля",
    responses={
        **get_auth_responses(400, 422),
    }
)
async def reset_password(data: ResetPasswordRequest):
    return MessageResponse(message="Пароль успешно изменён")