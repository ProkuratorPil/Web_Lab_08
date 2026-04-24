# main_fastapi.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
import logging
import os

from app.routers import user_router
from app.routers import file_router
from app.routers.auth_router import router as auth_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Определяем окружение
IS_PRODUCTION = os.getenv('NODE_ENV') == 'production'

# В production отключаем документацию
app = FastAPI(
    title="Lab Project API",
    description="Документация API для лабораторных работ №2-№4",
    version="1.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)

# Кастомная OpenAPI схема с настройками безопасности (только в dev)
if not IS_PRODUCTION:
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title="Lab Project API",
            version="1.0",
            description="Документация API для лабораторных работ №2-№4",
            routes=app.routes,
        )
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}

        openapi_schema["components"]["securitySchemes"] = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT токен, получаемый после авторизации. Также поддерживается передача через Cookie."
            },
            "cookieAuth": {
                "type": "apiKey",
                "in": "cookie",
                "name": "access_token",
                "description": "JWT токен доступа, хранящийся в HttpOnly cookie"
            },
            "oauth2": {
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": "https://oauth.yandex.ru/authorize",
                        "tokenUrl": "https://oauth.yandex.ru/token",
                        "scopes": {
                            "login:email": "Доступ к email пользователя",
                            "login:info": "Доступ к информации о профиле"
                        }
                    }
                },
                "description": "OAuth 2.0 авторизация через Яндекс"
            }
        }
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Глобальная обработка исключений
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик ошибок."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера"}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTP исключений."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# Подключение роутеров
app.include_router(auth_router)
app.include_router(user_router.router)
app.include_router(file_router.router)


@app.get("/", tags=["System"])
def read_root():
    return {"message": "Welcome to the Lab Project API"}


@app.get("/health", tags=["System"], summary="Проверка работоспособности")
def health_check():
    """Healthcheck endpoint."""
    return {"status": "healthy"}
