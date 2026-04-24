"""
Общие схемы ответов для документации OpenAPI.
"""
from pydantic import BaseModel, Field
from typing import Optional


class ErrorResponse(BaseModel):
    """Стандартная схема ошибки."""
    detail: str = Field(
        ...,
        description="Описание ошибки",
        example="Пользователь не найден"
    )


class ValidationErrorResponse(BaseModel):
    """Схема ошибки валидации (422)."""
    detail: list[dict] = Field(
        ...,
        description="Список ошибок валидации",
        example=[
            {
                "loc": ["body", "email"],
                "msg": "value is not a valid email address",
                "type": "value_error.email"
            }
        ]
    )


class MessageResponse(BaseModel):
    """Универсальная схема ответа с сообщением."""
    message: str = Field(
        ...,
        description="Основное сообщение ответа",
        example="Операция выполнена успешно"
    )
    detail: Optional[str] = Field(
        None,
        description="Дополнительная информация (опционально)",
        example="Пользователь создан с ID: 123"
    )


# Примеры ошибок для переиспользования в роутерах
ERROR_EXAMPLES = {
    400: {
        "model": ErrorResponse,
        "description": "Ошибка валидации или бизнес-логики",
        "content": {
            "application/json": {
                "example": {"detail": "Некорректные данные запроса"}
            }
        }
    },
    401: {
        "model": ErrorResponse,
        "description": "Необходима аутентификация",
        "content": {
            "application/json": {
                "example": {"detail": "Не авторизован"}
            }
        }
    },
    403: {
        "model": ErrorResponse,
        "description": "Недостаточно прав доступа",
        "content": {
            "application/json": {
                "example": {"detail": "Нет прав на выполнение операции"}
            }
        }
    },
    404: {
        "model": ErrorResponse,
        "description": "Ресурс не найден",
        "content": {
            "application/json": {
                "example": {"detail": "Ресурс не найден"}
            }
        }
    },
    422: {
        "model": ValidationErrorResponse,
        "description": "Ошибка валидации данных",
        "content": {
            "application/json": {
                "example": {
                    "detail": [
                        {
                            "loc": ["body", "email"],
                            "msg": "value is not a valid email address",
                            "type": "value_error.email"
                        }
                    ]
                }
            }
        }
    },
    500: {
        "model": ErrorResponse,
        "description": "Внутренняя ошибка сервера",
        "content": {
            "application/json": {
                "example": {"detail": "Внутренняя ошибка сервера"}
            }
        }
    }
}


def get_auth_responses(*codes: int) -> dict:
    """
    Возвращает словарь responses для эндпоинтов с указанными кодами ошибок.
    """
    return {code: ERROR_EXAMPLES[code] for code in codes if code in ERROR_EXAMPLES}
