# Теория: Лабораторная работа №4 — Автоматизированное документирование REST API (OpenAPI/Swagger)

## Содержание
1. [OpenAPI vs Swagger UI](#1-что-такое-спецификация-openapi-и-чем-она-отличается-от-swagger-ui)
2. [Code-First vs Design-First](#2-подходы-к-созданию-документации)
3. [Безопасность документации в Production](#3-скрытие-документации-в-боевой-среде)
4. [Схемы безопасности с HttpOnly Cookies](#4-документирование-схем-безопасности)
5. [Примеры в документации API](#5-зачем-нужны-примеры)
6. [HTTP коды для CRUD операций](#6-обязательные-http-коды)

---

## 1. Что такое спецификация OpenAPI и чем она отличается от Swagger UI?

### OpenAPI Specification (OAS)
**OpenAPI** — это формальная спецификация (стандарт) для описания REST API в формате JSON или YAML. Она определяет:
- Доступные эндпоинты и HTTP-методы
- Параметры запросов (query, path, header, cookie)
- Схемы данных (DTO) с типами, валидацией, примерами
- Схемы аутентификации и авторизации
- Коды ответов и примеры ошибок

**Версии:** OpenAPI 2.0 (Swagger 2.0), OpenAPI 3.0, OpenAPI 3.1 (текущая).

### Swagger UI
**Swagger UI** — это интерактивный веб-интерфейс (HTML+JS), который **визуализирует** OpenAPI спецификацию. Он позволяет:
- Просматривать все эндпоинты в удобном виде
- Отправлять тестовые запросы прямо из браузера
- Авторизовываться и тестировать защищённые методы
- Скачивать спецификацию в JSON/YAML

### Ключевое отличие
| OpenAPI | Swagger UI |
|---------|-----------|
| Машиночитаемый формат (JSON/YAML) | Человекочитаемый интерфейс (HTML) |
| Описывает **что** делает API | Показывает **как** с ним работать |
| Используется для генерации клиентов | Используется для ручного тестирования |
| Может быть написан вручную | Генерируется автоматически из OpenAPI |

**Аналогия:** OpenAPI — это чертёж здания, Swagger UI — это 3D-макет, который можно "потрогать".

### Применение в проекте
```python
# main.py — генерация OpenAPI спецификации
openapi_schema = get_openapi(
    title="Lab Project API",
    version="1.0",
    description="Документация API для лабораторных работ №2-№4",
    routes=app.routes,
)

# Доступно по адресам:
# /openapi.json — сырые данные спецификации (JSON)
# /docs — Swagger UI (интерактивный интерфейс)
# /redoc — ReDoc (альтернативный просмотрщик)
```

---

## 2. Подходы к созданию документации: Code-First и Design-First

### Design-First (Contract-First)
1. Сначала пишется спецификация OpenAPI вручную (YAML/JSON)
2. На основе спецификации генерируется код сервера и клиентов
3. Команды фронтенда и бэкенда работают параллельно по контракту

**Плюсы:**
- Чёткий контракт между командами до начала разработки
- Возможность параллельной работы
- Легко генерировать SDK для разных языков

**Минусы:**
- Спецификация быстро устаревает, если не поддерживать
- Требует дисциплины: сначала документ, потом код
- Сложно поддерживать синхронизацию

### Code-First
1. Сначала пишется код приложения
2. Документация генерируется автоматически из кода (аннотации, декораторы, типы)
3. Спецификация всегда актуальна, так как она — побочный продукт кода

**Плюсы:**
- Документация всегда синхронизирована с кодом
- Не требует ручного написания YAML/JSON
- Быстрая разработка: пишешь код — получаешь документацию

**Минусы:**
- Спецификация получается "технической", требует аннотаций для читаемости
- Сложно использовать для планирования до начала разработки
- Генерация клиентских SDK может быть менее гибкой

### Что использовалось в проекте
**Code-First** — FastAPI автоматически сканирует:
- Pydantic-модели (DTO) с `Field(description=..., example=...)`
- Декораторы роутеров (`@router.get(...)`, `@router.post(...)`)
- Зависимости (`Depends`) для security
- Типы возвращаемых значений

```python
# app/schemas/auth.py — Pydantic схема автоматически попадает в OpenAPI
class UserRegister(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Уникальное имя пользователя (латиница и цифры)",
        example="john_doe"
    )
    email: EmailStr = Field(..., description="Email пользователя", example="john.doe@example.com")
```

```python
# app/routers/auth_router.py — декораторы роутера аннотируют эндпоинт
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="Создаёт нового пользователя с указанными данными.",
    response_description="Данные созданного пользователя",
    responses={
        400: {"description": "Ошибка валидации или бизнес-логики"},
        422: {"description": "Ошибка валидации данных"},
    }
)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    ...
```

---

## 3. Почему важно скрывать документацию API в "боевой" среде?

### Риски открытой документации в Production

| Риск | Описание |
|------|----------|
| **Информационное раскрытие** | Злоумышленник видит все эндпоинты, параметры, схемы данных — это упрощает поиск уязвимостей |
| **Атаки на скрытые эндпоинты** | Даже "внутренние" API становятся известны (например, `/admin`, `/debug`) |
| **Утечка структуры БД** | Схемы DTO могут раскрывать структуру таблиц базы данных |
| **DoS-атаки** | Злоумышленник знает, какие запросы ресурсоёмки, и может целенаправленно нагружать систему |
| **Обход аутентификации** | Документация показывает, какие эндпоинты публичные, а какие защищённые — упрощает поиск ошибок авторизации |
| **Сканирование уязвимостей** | Автоматические сканеры (Burp, OWASP ZAP) используют `/openapi.json` для составления карты атаки |

### Реализация в проекте
```python
# main.py — условное отключение документации в production
IS_PRODUCTION = os.getenv('NODE_ENV') == 'production'

app = FastAPI(
    docs_url=None if IS_PRODUCTION else "/docs",       # Swagger UI
    redoc_url=None,                                     # ReDoc (кастомный эндпоинт)
    openapi_url=None if IS_PRODUCTION else "/openapi.json",  # OpenAPI JSON
)
```

**Как работает:**
- В `development` (`.env`: `NODE_ENV=development`) — документация доступна
- В `production` (`.env`: `NODE_ENV=production`) — эндпоинты `/docs`, `/openapi.json` возвращают `404 Not Found`
- Переменная `NODE_ENV` передаётся в `docker-compose.yml`:
  ```yaml
  environment:
    NODE_ENV: ${NODE_ENV:-development}
  ```

---

## 4. Как правильно документировать схемы безопасности с HttpOnly Cookies?

### HttpOnly Cookies vs Bearer Token
| Способ | Передача | Безопасность |
|--------|----------|-------------|
| **Bearer Token** | Заголовок `Authorization: Bearer <token>` | Токен виден в JavaScript, может быть украден XSS |
| **HttpOnly Cookie** | Cookie `access_token` с флагом `HttpOnly` | Недоступен для JavaScript, защита от XSS |

### Схемы безопасности в OpenAPI

#### 1. `http` (Bearer)
Для JWT токена, передаваемого в заголовке:
```yaml
securitySchemes:
  bearerAuth:
    type: http
    scheme: bearer
    bearerFormat: JWT
    description: JWT токен, получаемый после авторизации
```

#### 2. `apiKey` (Cookie)
Для токена в HttpOnly cookie — это **ключевой момент**, потому что стандарт OpenAPI не имеет нативной схемы "cookie auth". Используем `apiKey` с `in: cookie`:
```yaml
securitySchemes:
  cookieAuth:
    type: apiKey
    in: cookie
    name: access_token
    description: JWT токен доступа, хранящийся в HttpOnly cookie
```

> ⚠️ **Важно:** Swagger UI поддерживает схему `apiKey` с `in: cookie`, но фактически cookie отправляются браузером автоматически (если домен и путь совпадают). В интерфейсе Swagger UI эта схема отображается для информации.

#### 3. `oauth2`
Для OAuth 2.0 Authorization Code Grant:
```yaml
securitySchemes:
  oauth2:
    type: oauth2
    flows:
      authorizationCode:
        authorizationUrl: https://oauth.yandex.ru/authorize
        tokenUrl: https://oauth.yandex.ru/token
        scopes:
          login:email: "Доступ к email пользователя"
          login:info: "Доступ к информации о профиле"
```

### Применение в проекте
```python
# main.py — настройка securitySchemes в OpenAPI
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
        }
    }
}
```

```python
# app/routers/user_router.py — указание security для защищённых эндпоинтов
@router.get(
    "/",
    ...,
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
def get_users(...):
    ...
```

```python
# app/core/dependencies.py — извлечение токена из Cookie ИЛИ заголовка
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    access_token: Optional[str] = Cookie(default=None, alias="access_token"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    token = None
    if access_token:           # Сначала пробуем Cookie
        token = access_token
    elif credentials:          # Затем заголовок Authorization
        token = credentials.credentials
    ...
```

---

## 5. Зачем нужны примеры в документации API?

### Роль примеров (Examples)

| Цель | Описание |
|------|----------|
| **Понимание формата** | Потребитель видит, как выглядит реальный запрос/ответ, а не просто типы полей |
| **Быстрый старт** | Копирует пример, меняет значения — и готовый запрос |
| **Тестирование** | В Swagger UI пример автоматически подставляется в форму запроса |
| **Снижение ошибок** | Чёткие границы значений (min/max length, формат email, UUID) |
| **Коммуникация** | Фронтенд и бэкенд разработчики имеют общее понимание контракта |

### Где должны быть примеры
1. **В DTO (Pydantic моделях)** — примеры полей
2. **В ответах ошибок** — примеры тел ошибок для каждого кода
3. **В success-ответах** — примеры успешных ответов

### Применение в проекте

```python
# app/schemas/auth.py — примеры в Pydantic полях
class UserRegister(BaseModel):
    username: str = Field(..., example="john_doe")
    email: EmailStr = Field(..., example="john.doe@example.com")
    password: str = Field(..., example="SecurePassword123")
```

```python
# app/schemas/common.py — примеры ошибок
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
    ...
}
```

```python
# app/routers/auth_router.py — примеры ошибок для каждого эндпоинта
@router.post(
    "/register",
    ...,
    responses={
        **get_auth_responses(400, 422),  # Подключает примеры ошибок 400 и 422
    }
)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    ...
```

---

## 6. Какие HTTP коды ответов обязательно должны быть описаны для CRUD операций?

### Универсальные коды для любого API

| Код | Название | Когда использовать |
|-----|----------|-------------------|
| **200** | OK | Успешный GET, PUT, PATCH — данные возвращены/обновлены |
| **201** | Created | Успешный POST — ресурс создан |
| **204** | No Content | Успешный DELETE — ресурс удалён, тело пустое |
| **400** | Bad Request | Ошибка валидации входных данных (неверный формат, отсутствующие поля) |
| **401** | Unauthorized | Пользователь не аутентифицирован (нет токена или он невалидный) |
| **403** | Forbidden | Пользователь аутентифицирован, но не имеет прав (например, пытается редактировать чужой профиль) |
| **404** | Not Found | Ресурс не найден (пользователь с таким ID не существует) |
| **422** | Unprocessable Entity | Ошибка валидации Pydantic (автоматически в FastAPI) |
| **500** | Internal Server Error | Необработанное исключение сервера |

### Матрица кодов по CRUD операциям

| Операция | Успех | Ошибки клиента | Ошибки сервера |
|----------|-------|---------------|----------------|
| **CREATE (POST)** | 201 Created | 400, 422 | 500 |
| **READ (GET list)** | 200 OK | 401, 403 | 500 |
| **READ (GET one)** | 200 OK | 401, 403, 404 | 500 |
| **UPDATE (PUT/PATCH)** | 200 OK | 400, 401, 403, 404, 422 | 500 |
| **DELETE** | 204 No Content | 401, 403, 404 | 500 |

### Применение в проекте

```python
# app/routers/user_router.py — все CRUD с кодами ответов

# CREATE
@router.post("/", ..., status_code=status.HTTP_201_CREATED,
    responses={**get_auth_responses(400, 422)})
def create_user(...):
    ...

# READ list
@router.get("/", ..., responses={**get_auth_responses(401, 403, 404, 422)})
def get_users(...):
    ...

# READ one
@router.get("/{user_id}", ..., responses={**get_auth_responses(401, 403, 404)})
def get_user(...):
    ...

# UPDATE
@router.put("/{user_id}", ..., responses={**get_auth_responses(401, 403, 404, 422)})
def update_user_full(...):
    ...

@router.patch("/{user_id}", ..., responses={**get_auth_responses(401, 403, 404, 422)})
def update_user_partial(...):
    ...

# DELETE
@router.delete("/{user_id}", ..., status_code=status.HTTP_204_NO_CONTENT,
    responses={**get_auth_responses(401, 403, 404)})
def delete_user(...):
    ...
```

```python
# app/schemas/common.py — централизованные примеры ошибок
def get_auth_responses(*codes: int) -> dict:
    """Возвращает словарь responses для указанных кодов ошибок."""
    return {code: ERROR_EXAMPLES[code] for code in codes if code in ERROR_EXAMPLES}
```

---

## Итог: Архитектура документации в проекте

```
┌─────────────────────────────────────────┐
│  FastAPI App                            │
│  ┌─────────────────────────────────┐    │
│  │  main.py                        │    │
│  │  • Условное отключение /docs    │    │
│  │    (production vs development)  │    │
│  │  • Настройка securitySchemes    │    │
│  │  • Кастомный /redoc эндпоинт    │    │
│  └─────────────────────────────────┘    │
│              │                          │
│  ┌───────────┴───────────┐              │
│  ▼                       ▼              │
│  ┌─────────────┐   ┌─────────────┐      │
│  │ /docs       │   │ /redoc      │      │
│  │ Swagger UI  │   │ ReDoc       │      │
│  └─────────────┘   └─────────────┘      │
│       │                  │              │
│       └────────┬─────────┘              │
│                ▼                        │
│         ┌─────────────┐                 │
│         │ /openapi.json│                │
│         │ OpenAPI 3.1  │                │
│         └─────────────┘                 │
│                ▲                        │
│  ┌─────────────┴─────────────┐         │
│  │ Роутеры + Pydantic схемы  │         │
│  │ • auth_router.py          │         │
│  │ • user_router.py          │         │
│  │ • file_router.py          │         │
│  │ • schemas/*.py            │         │
│  └───────────────────────────┘         │
└─────────────────────────────────────────┘
```

**Ключевые файлы:**
- `main.py` — конфигурация FastAPI, условное отключение документации, securitySchemes, кастомный ReDoc
- `app/routers/*.py` — аннотации эндпоинтов (summary, description, responses, security)
- `app/schemas/*.py` — Pydantic DTO с Field(description, example)
- `app/schemas/common.py` — централизованные схемы ошибок с примерами
- `.env.example` / `docker-compose.yml` — переменная `NODE_ENV` для управления доступом
