# User & File Management API v2.0

RESTful API для управления пользователями и файлами с JWT аутентификацией и OAuth 2.0.

## Возможности

- 🔐 **JWT Аутентификация** - Access и Refresh токены с хешированием
- 🔑 **OAuth 2.0** - Вход через Яндекс и VK
- 🔒 **Безопасность** - Хеширование паролей с солью (bcrypt), защита токенов
- 👤 **Soft Delete** - Восстанавливаемые удалённые записи
- 📄 **DTO Валидация** - Pydantic модели для всех запросов/ответов
- 🐳 **Docker Ready** - Контейнеризация с healthcheck

## Быстрый старт

### 1. Настройка переменных окружения

Скопируйте `.env.example` в `.env` и заполните значения:

```bash
cp .env.example .env
```

**Обязательные переменные:**
- `JWT_ACCESS_SECRET` - Секретный ключ для Access токена
- `JWT_REFRESH_SECRET` - Секретный ключ для Refresh токена
- `YANDEX_CLIENT_ID` / `YANDEX_CLIENT_SECRET` - Данные OAuth приложения Яндекс
- `VK_CLIENT_ID` / `VK_CLIENT_SECRET` - Данные OAuth приложения VK

### 2. Запуск через Docker

```bash
docker-compose up --build
```

Приложение будет доступно на `http://localhost:4200`

## API Endpoints

### Аутентификация `/auth`

| Метод | URI | Описание | Доступ |
|-------|-----|---------|--------|
| POST | `/auth/register` | Регистрация | Public |
| POST | `/auth/login` | Вход | Public |
| POST | `/auth/refresh` | Обновление токенов | Public (нужен Refresh Cookie) |
| GET | `/auth/whoami` | Данные текущего пользователя | Private |
| POST | `/auth/logout` | Завершение сессии | Private |
| POST | `/auth/logout-all` | Завершение всех сессий | Private |
| GET | `/auth/oauth/{provider}` | Инициация OAuth | Public |
| GET | `/auth/oauth/{provider}/callback` | OAuth Callback | Public |
| POST | `/auth/forgot-password` | Запрос сброса пароля | Public |
| POST | `/auth/reset-password` | Установка нового пароля | Public |

### Пользователи `/users`

| Метод | URI | Описание | Доступ |
|-------|-----|---------|--------|
| POST | `/users/` | Создание пользователя | Public |
| GET | `/users/` | Список пользователей | Private |
| GET | `/users/{id}` | Получить пользователя | Private |
| PUT | `/users/{id}` | Полное обновление | Private (владелец) |
| PATCH | `/users/{id}` | Частичное обновление | Private (владелец) |
| DELETE | `/users/{id}` | Удаление | Private (владелец) |

### Файлы `/files`

| Метод | URI | Описание | Доступ |
|-------|-----|---------|--------|
| POST | `/files/` | Создание записи о файле | Private |
| GET | `/files/` | Список файлов | Private (свои) |
| GET | `/files/{id}` | Получить файл | Private (владелец) |
| PUT | `/files/{id}` | Обновление | Private (владелец) |
| PATCH | `/files/{id}` | Частичное обновление | Private (владелец) |
| DELETE | `/files/{id}` | Удаление | Private (владелец) |

## Примеры использования

### Регистрация

```bash
curl.exe -X POST http://localhost:4200/auth/register -H "Content-Type: application/json" -d '{"username": "testuser", "email": "test@example.com", "password": "SecurePass123"}'
```

### Вход

```bash
curl -X POST http://localhost:4200/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123"
  }'
```

### Проверка статуса (нужен Cookie)

```bash
curl -X GET http://localhost:4200/auth/whoami \
  -b cookies.txt
```

### OAuth Яндекс

1. Перейдите на `http://localhost:4200/auth/oauth/yandex`
2. Авторизуйтесь в Яндексе
3. Бrowser перенаправит на `/` с установленными cookies

## Безопасность

### Cookies
- `HttpOnly` - Защита от XSS
- `Secure` - Только HTTPS (в production)
- `SameSite=Lax` - Защита от CSRF

### Токены
- Access Token: 15 минут
- Refresh Token: 7 дней
- Токены хешируются перед сохранением в БД

### Пароли
- Хеширование bcrypt с автоматической солью
- Минимум 8 символов, заглавные, строчные, цифры

## Архитектура

```
app/
├── core/
│   ├── config.py       # Настройки из .env
│   ├── database.py     # SQLAlchemy engine
│   ├── security.py     # Хеширование паролей и токенов
│   ├── jwt.py          # Генерация и валидация JWT
│   ├── dependencies.py # FastAPI dependencies
│   └── oauth/
│       └── providers.py # OAuth провайдеры
├── models/
│   ├── user.py         # Модель User
│   ├── token.py        # Модель Token
│   └── uploaded_file.py # Модель File
├── schemas/
│   ├── auth.py         # DTO для аутентификации
│   ├── user.py         # DTO для пользователей
│   └── file.py         # DTO для файлов
├── crud/
│   ├── book.py         # CRUD пользователей
│   ├── file_crud.py    # CRUD файлов
│   └── token_crud.py   # CRUD токенов
├── services/
│   ├── user_service.py # Бизнес-логика пользователей
│   └── file_service.py # Бизнес-логика файлов
└── routers/
    ├── auth_router.py  # Эндпоинты аутентификации
    ├── user_router.py  # Эндпоинты пользователей
    └── file_router.py  # Эндпоинты файлов
```

## Тестирование

```bash
# Запуск всех тестов
pytest

# Тест конкретного модуля
pytest tests/test_auth.py -v
```

## TODO

- [ ] Реализация отправки email для сброса пароля
- [ ] Система ролей (Admin, User)
- [ ] Rate limiting
- [ ] Документация Swagger/OpenAPI
- [ ] Юнит-тесты
- [ ] Redis для хранения OAuth state
