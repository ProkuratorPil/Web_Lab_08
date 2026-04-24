from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.user_service import UserService
from app.schemas.user import UserCreate, UserUpdate, UserResponse, PaginationParams, PaginatedResponse
from app.schemas.common import get_auth_responses

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создание нового пользователя",
    description="Создает нового пользователя с указанными данными. Пользователь создается неактивированным.",
    response_description="Данные созданного пользователя",
    responses={
        **get_auth_responses(400, 422),
    }
)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Создание нового пользователя.
    Доступ: Public
    """
    service = UserService(db)
    user = service.create(user_data)
    return user


@router.get(
    "/",
    response_model=PaginatedResponse,
    summary="Получение списка пользователей",
    description="Возвращает пагинированный список всех активных пользователей. Доступ только для авторизованных.",
    response_description="Пагинированный список пользователей",
    responses={
        **get_auth_responses(401, 403, 404, 422),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
def get_users(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение списка пользователей (пагинированный).
    Доступ: Private (только авторизованные)
    """
    service = UserService(db)
    users, total = service.get_all_active(pagination)
    total_pages = (total + pagination.limit - 1) // pagination.limit
    return {
        "data": users,
        "meta": {
            "total": total,
            "page": pagination.page,
            "limit": pagination.limit,
            "totalPages": total_pages,
        }
    }


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Получение пользователя по ID",
    description="Возвращает данные пользователя по указанному ID. Доступ только для авторизованных.",
    response_description="Данные пользователя",
    responses={
        **get_auth_responses(401, 403, 404),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение пользователя по ID.
    Доступ: Private (только авторизованные)
    """
    service = UserService(db)
    user = service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Полное обновление пользователя",
    description="Обновляет все поля пользователя (PUT). Пользователь может редактировать только свой профиль.",
    response_description="Данные обновленного пользователя",
    responses={
        **get_auth_responses(401, 403, 404, 422),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
def update_user_full(
    user_id: UUID,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Полное обновление пользователя (PUT).
    Доступ: Private (только владелец или админ)
    """
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на редактирование этого пользователя"
        )

    service = UserService(db)
    user = service.update(user_id, user_data, partial=False)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Частичное обновление пользователя",
    description="Обновляет указанные поля пользователя (PATCH). Пользователь может редактировать только свой профиль.",
    response_description="Данные обновленного пользователя",
    responses={
        **get_auth_responses(401, 403, 404, 422),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
def update_user_partial(
    user_id: UUID,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Частичное обновление пользователя (PATCH).
    Доступ: Private (только владелец или админ)
    """
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на редактирование этого пользователя"
        )

    service = UserService(db)
    user = service.update(user_id, user_data, partial=True)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление пользователя (Soft Delete)",
    description="Помечает пользователя как удаленного (Soft Delete). Пользователь может удалить только свой профиль.",
    responses={
        **get_auth_responses(401, 403, 404),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Удаление пользователя (Soft Delete).
    Доступ: Private (только владелец)
    """
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на удаление этого пользователя"
        )

    service = UserService(db)
    deleted = service.delete(user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return None
