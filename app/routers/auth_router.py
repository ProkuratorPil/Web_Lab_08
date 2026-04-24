"""
Роутер аутентификации и авторизации.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import secrets

from app.core.database import get_db
from app.core.jwt import create_tokens, jwt_manager, verify_refresh
from app.core.security import hash_password, verify_password, hash_token
from app.core.dependencies import (
    get_current_user,
    validate_refresh_token,
    get_client_ip,
    get_user_agent
)
from app.core.oauth.providers import OAuthProviderFactory, get_oauth_user_info
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
from app.models.user import User
from app.models.token import TokenType
from app.crud.token_crud import create_token, revoke_token, revoke_all_user_tokens, get_token_by_hash


router = APIRouter(prefix="/auth", tags=["Auth"])


oauth_states = {}


def set_auth_cookies(response, access_token, refresh_token, access_expires, refresh_expires):
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="lax", max_age=900)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="lax", max_age=604800)


def clear_auth_cookies(response):
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")


def get_oauth_providers_list(user: User) -> list[str]:
    providers = []
    if user.yandex_id:
        providers.append("yandex")
    if user.vk_id:
        providers.append("vk")
    return providers


def _save_tokens(db: Session, user_id, tokens: dict, ip: str, ua: str):
    create_token(
        db=db,
        user_id=user_id,
        token=tokens["access_token"],
        token_type=TokenType.access,
        user_agent=ua,
        ip_address=ip,
        expires_at=datetime.now(timezone.utc) + jwt_manager.access_expires_delta
    )
    create_token(
        db=db,
        user_id=user_id,
        token=tokens["refresh_token"],
        token_type=TokenType.refresh,
        user_agent=ua,
        ip_address=ip,
        expires_at=datetime.now(timezone.utc) + jwt_manager.refresh_expires_delta
    )


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
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email, User.deleted_at.is_(None)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь с таким email уже существует")

    existing = db.query(User).filter(User.username == user_data.username.lower(), User.deleted_at.is_(None)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь с таким username уже существует")

    hashed_password, salt = hash_password(user_data.password)

    user = User(
        username=user_data.username.lower(),
        email=user_data.email.lower(),
        hashed_password=hashed_password,
        password_salt=salt,
        phone=user_data.phone,
        is_verified=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

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
async def login(response: Response, request: Request, user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email.lower(), User.deleted_at.is_(None)).first()

    if not user or not user.hashed_password or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Аккаунт деактивирован")

    tokens = create_tokens(user.id)
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    _save_tokens(db, user.id, tokens, ip, ua)

    set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"], tokens["access_expires_at"], tokens["refresh_expires_at"])
    return TokenResponse(**tokens)


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
async def refresh_tokens(response: Response, request: Request, result: tuple = Depends(validate_refresh_token), db: Session = Depends(get_db)):
    user, old_refresh_token = result
    old_token_hash = hash_token(old_refresh_token)
    tokens = create_tokens(user.id)
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    _save_tokens(db, user.id, tokens, ip, ua)

    old_token = get_token_by_hash(db, old_token_hash)
    if old_token:
        old_token.is_revoked = True
        db.commit()

    set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"], tokens["access_expires_at"], tokens["refresh_expires_at"])
    return TokenResponse(**tokens)


@router.get(
    "/whoami",
    response_model=UserProfile,
    summary="Информация о текущем пользователе",
    description="Возвращает профиль авторизованного пользователя.",
    response_description="Данные профиля пользователя",
    responses={
        **get_auth_responses(401),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
async def whoami(current_user: User = Depends(get_current_user)):
    return UserProfile(
        id=current_user.id, username=current_user.username, email=current_user.email, phone=current_user.phone,
        is_verified=current_user.is_verified, is_oauth_user=current_user.is_oauth_user,
        created_at=current_user.created_at, oauth_providers=get_oauth_providers_list(current_user)
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Выход из системы",
    description="Завершает текущую сессию: отзывает refresh токен и очищает cookies.",
    response_description="Подтверждение выхода",
    responses={
        **get_auth_responses(401),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
async def logout(response: Response, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        token_hash = hash_token(refresh_token)
        token = get_token_by_hash(db, token_hash)
        if token and token.user_id == current_user.id:
            token.is_revoked = True
            db.commit()
    clear_auth_cookies(response)
    return MessageResponse(message="Сессия завершена")


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    summary="Выход из всех сессий",
    description="Отзывает все токены пользователя и очищает cookies.",
    response_description="Подтверждение отзыва всех сессий",
    responses={
        **get_auth_responses(401),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
async def logout_all(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = revoke_all_user_tokens(db, current_user.id)
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
async def oauth_callback(provider: str, code: str, state: str, response: Response, request: Request, db: Session = Depends(get_db)):
    provider_name = provider.lower()
    if state not in oauth_states or oauth_states[state] != provider_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный state")
    del oauth_states[state]
    user_info = await get_oauth_user_info(provider_name, code)
    if not user_info:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не удалось получить данные от провайдера")
    provider_user_id = user_info.get("provider_user_id")
    provider_id_field = f"{provider_name}_id"
    user = db.query(User).filter(getattr(User, provider_id_field) == provider_user_id, User.deleted_at.is_(None)).first()
    if not user:
        email = user_info.get("email")
        if email:
            user = db.query(User).filter(User.email == email.lower(), User.deleted_at.is_(None)).first()
        if user:
            setattr(user, provider_id_field, provider_user_id)
            if not user.is_verified:
                user.is_verified = True
        else:
            username = user_info.get("username") or f"{provider_name}_{provider_user_id}"
            user = User(username=username.lower(), email=(email or f"{provider_user_id}@{provider_name}.oauth").lower(), is_verified=True, **{provider_id_field: provider_user_id})
            db.add(user)
    db.commit()
    db.refresh(user)
    tokens = create_tokens(user.id)
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    _save_tokens(db, user.id, tokens, ip, ua)
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
async def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
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
async def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    return MessageResponse(message="Пароль успешно изменён")
