# Лабораторная работа №5: Кеширование данных и управление сессиями с использованием Redis

RESTful API сервис для управления пользователями и файлами с JWT аутентификацией, OAuth 2.0, и **системой кеширования на базе Redis**.

## 📋 Содержание
- [Описание](#описание)
- [Технологии](#технологии)
- [Установка и запуск](#установка-и-запуск)
- [Redis CLI](#redis-cli)
- [Архитектура](#архитектура)
- [Стратегия кеширования](#стратегия-кеширования)
- [Управление сессиями через JTI](#управление-сессиями-через-jti)
- [Эндпоинты и кеш](#эндпоинты-и-кеш)
- [Аутентификация](#аутентификация)
- [Безопасность кеша](#безопасность-кеша)
- [Авторы](#авторы)

## 📝 Описание

Реализация полноценного REST API с:
- CRUD операциями над пользователями и файлами
- JWT аутентификацией (access + refresh токены в HttpOnly cookies)
- **Кешированием часто запрашиваемых данных через Redis (Cache-Aside)**
- **Хранением идентификаторов Access токенов (JTI) в Redis для мгновенного отзыва сессий**
- Инвалидацией кеша при операциях записи (Create, Update, Delete)
- OAuth 2.0 авторизацией через Яндекс и VK
- Автоматической генерацией OpenAPI 3.0 документации из кода (Code-First)
- Пагинацией, валидацией и обработкой ошибок

## 🛠 Технологии

| Компонент | Версия |
|-----------|--------|
| Python | 3.12+ |
| FastAPI | 0.115+ |
| SQLAlchemy | 2.0+ |
| PostgreSQL | 16 |
| **Redis** | **7** |
| Pydantic | 2.0+ |
| Uvicorn | 0.30+ |
| redis-py | 5.0+ |

## 🚀 Установка и запуск

### 1. Клонирование репозитория
```bash
git clone https://github.com/ProkuratorPil/WB_Lab_5.git
cd WB_Lab_5
```

### 2. Настройка окружения
Скопируйте пример конфигурации и заполните переменные:
```bash
cp .env.example .env
```

Обязательные параметры в `.env`:
```ini
# База данных
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=lab_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_secure_password_change_in_prod
CACHE_TTL_DEFAULT=300

# JWT ключи
JWT_ACCESS_SECRET=your_secret_key
JWT_REFRESH_SECRET=your_refresh_key

# OAuth провайдеры
YANDEX_CLIENT_ID=your_client_id
YANDEX_CLIENT_SECRET=your_client_secret

# Окружение (development | production)
NODE_ENV=development
```

### 3. Запуск через Docker Compose (рекомендуется)
```bash
docker-compose up --build -d
```

Сервисы будут доступны:
- API: `http://localhost:4200`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

### 4. Локальный запуск (без Docker)
```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск PostgreSQL и Redis (должны быть запущены отдельно)

# Применение миграций
alembic upgrade head

# Запуск сервиса
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 🧰 Redis CLI

Подключение к Redis внутри контейнера:
```bash
docker exec -it wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod
```

Полезные команды для проверки:
```bash
# Просмотр ключей по паттерну
KEYS 'wp:*'

# Получение значения ключа
GET wp:users:list:page:1:limit:10

# Проверка TTL ключа
TTL wp:users:list:page:1:limit:10

# Удаление ключа (ручная инвалидация)
DEL wp:users:list:page:1:limit:10

# Удаление по паттерну (массовая инвалидация)
UNLINK wp:users:*

# Очистка всей базы (для тестов)
FLUSHDB
```

## 🏗 Архитектура

```
app/
├── core/           # Конфигурация, безопасность, утилиты, OAuth, кеш
│   ├── config.py
│   ├── database.py
│   ├── jwt.py              # Генерация токенов с JTI
│   ├── dependencies.py     # Проверка JTI в Redis
│   ├── cache.py            # Сервис кеширования (Redis)
│   └── oauth/
├── models/         # SQLAlchemy модели
├── schemas/        # Pydantic схемы (DTO)
├── crud/           # Операции с базой данных
├── services/       # Бизнес логика с инвалидацией кеша
├── routers/        # Роутеры API
│   ├── auth_router.py      # Управление JTI в Redis
│   ├── user_router.py
│   └── file_router.py
└── __init__.py
```

## 📦 Стратегия кеширования

Используется паттерн **Cache-Aside (Lazy Loading)**:
1. При запросе сначала проверяется кеш
2. При **Cache Hit** — данные возвращаются из Redis
3. При **Cache Miss** — данные загружаются из БД, сохраняются в кеш с TTL, и возвращаются клиенту

### Именование ключей

Формат: `app:module:entity:identifier`

| Ключ | Описание | TTL |
|------|----------|-----|
| `wp:users:list:page:{page}:limit:{limit}` | Пагинированный список пользователей | 300 сек |
| `wp:users:detail:{userId}` | Данные конкретного пользователя | 300 сек |
| `wp:users:profile:{userId}` | Профиль пользователя (`/auth/whoami`) | 300 сек |
| `wp:auth:user:{userId}:access:{jti}` | JTI Access токена (валидность сессии) | 900 сек (15 мин) |

## 🔐 Управление сессиями через JTI

Access токен содержит уникальный идентификатор **JTI (JWT ID)**.

### Хранение в Redis
При генерации Access токена создаётся запись:
```
wp:auth:user:{userId}:access:{jti} = "valid"
```
с TTL, равным времени жизни токена (15 минут).

### Проверка
При каждом запросе к защищённым эндпоинтам:
1. Проверяется подпись JWT
2. Извлекается `jti` из payload
3. Проверяется наличие ключа `wp:auth:user:{userId}:access:{jti}` в Redis
4. Если ключа нет — возвращается `401 Unauthorized`

### Отзыв сессии (Logout)
При вызове `/auth/logout`:
- JTI текущего токена удаляется из Redis
- Кеш профиля пользователя инвалидируется
- Refresh токен отзывается в БД

При вызове `/auth/logout-all`:
- Удаляются **все** JTI пользователя по паттерну `wp:auth:user:{userId}:access:*`
- Инвалидируется кеш профиля

## 🔌 Эндпоинты и кеш

### 🔐 Аутентификация
| Метод | Путь | Действие с кешем | Доступ |
|-------|------|------------------|--------|
| POST | `/auth/register` | — | Публичный |
| POST | `/auth/login` | Создание JTI в Redis | Публичный |
| POST | `/auth/refresh` | Создание нового JTI, отзыв старого | Публичный |
| GET | `/auth/whoami` | Проверка кеша профиля | Приватный 🔒 |
| POST | `/auth/logout` | Удаление JTI и профиля из кеша | Приватный 🔒 |
| POST | `/auth/logout-all` | Удаление всех JTI и профиля | Приватный 🔒 |
| GET | `/auth/oauth/{provider}` | — | Публичный |
| GET | `/auth/oauth/{provider}/callback` | Создание JTI в Redis | Публичный |

### 👤 Пользователи
| Метод | Путь | Действие с кешем | Доступ |
|-------|------|------------------|--------|
| POST | `/users` | Инвалидация списков | Публичный |
| GET | `/users` | Проверка кеша списка | Приватный 🔒 |
| GET | `/users/{id}` | Проверка кеша детали | Приватный 🔒 |
| PUT | `/users/{id}` | Инвалидация списка + детали + профиля | Приватный 🔒 (владелец) |
| PATCH | `/users/{id}` | Инвалидация списка + детали + профиля | Приватный 🔒 (владелец) |
| DELETE | `/users/{id}` | Инвалидация списка + детали + профиля | Приватный 🔒 (владелец) |

### 📁 Файлы
| Метод | Путь | Описание | Доступ |
|-------|------|----------|--------|
| POST | `/files` | Создание записи о файле | Приватный 🔒 |
| GET | `/files` | Список файлов (пагинация) | Приватный 🔒 |
| GET | `/files/{id}` | Получение файла по ID | Приватный 🔒 (владелец) |
| PUT | `/files/{id}` | Полное обновление | Приватный 🔒 (владелец) |
| PATCH | `/files/{id}` | Частичное обновление | Приватный 🔒 (владелец) |
| DELETE | `/files/{id}` | Удаление (Soft Delete) | Приватный 🔒 (владелец) |

## 🔐 Аутентификация

### JWT через Cookies (основной способ)
При входе через `/auth/login` сервер устанавливает два HttpOnly cookie:
- `access_token` — действует 15 минут
- `refresh_token` — действует 7 дней

Cookies отправляются автоматически браузером при каждом запросе.

### JWT через Authorization заголовок
Также поддерживается передача токена в заголовке:
```
Authorization: Bearer <access_token>
```

### OAuth 2.0
Авторизация через внешних провайдеров (Яндекс, VK). После успешной авторизации устанавливаются те же JWT cookies.

## 🛡 Безопасность кеша

- ❌ **Запрещено** хранить пароли в кеше
- ❌ **Запрещено** хранить полные токены доступа в открытом виде (хранится только JTI)
- ✅ Используются **иерархические префиксы** ключей (`wp:users:...`, `wp:auth:...`)
- ✅ Все ключи имеют **TTL** (Time To Live)
- ✅ Подключение к Redis осуществляется с **паролем**
- ✅ При недоступности Redis приложение продолжает работать (degradation)

## 🧪 Тестирование

### 1. Кеширование списка пользователей
```bash
# Первый запрос — Cache Miss (запрос к БД)
curl -s -X GET "http://localhost:4200/users/?page=1&limit=10" -b cookies.txt

# Проверка ключа в Redis
docker exec wp_labs_redis redis-cli --pass $REDIS_PASSWORD get "wp:users:list:page:1:limit:10"

# Второй запрос — Cache Hit (ответ из Redis, без запроса к БД)
curl -s -X GET "http://localhost:4200/users/?page=1&limit=10" -b cookies.txt
```

### 2. Инвалидация кеша при обновлении
```bash
# Обновление пользователя — кеш списка должен быть удалён
curl -s -X PATCH "http://localhost:4200/users/{id}" -H "Content-Type: application/json" -d '{"phone":"+79991112233"}' -b cookies.txt

# Проверка — ключи wp:users:* должны отсутствовать
docker exec wp_labs_redis redis-cli --pass $REDIS_PASSWORD keys "wp:users:*"
```

### 3. Управление сессиями через JTI
```bash
# Вход в систему — JTI сохраняется в Redis
curl -s -X POST "http://localhost:4200/auth/login" -H "Content-Type: application/json" -d '{"email":"test@example.com","password":"SecurePass123"}' -c cookies.txt

# Проверка наличия JTI в Redis
docker exec wp_labs_redis redis-cli --pass $REDIS_PASSWORD keys "wp:auth:user:*:access:*"

# Выход — JTI удаляется
curl -s -X POST "http://localhost:4200/auth/logout" -b cookies.txt

# Повторный запрос с тем же токеном — 401 Unauthorized
curl -s -X GET "http://localhost:4200/auth/whoami" -b cookies.txt
```

## 📝 Переменные окружения

Полный список параметров конфигурации находится в файле `.env.example`.

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `NODE_ENV` | Окружение (`development` / `production`) | `development` |
| `DB_HOST` | Хост базы данных | `localhost` |
| `DB_PORT` | Порт базы данных | `5432` |
| `REDIS_HOST` | Хост Redis | `localhost` |
| `REDIS_PORT` | Порт Redis | `6379` |
| `REDIS_PASSWORD` | Пароль Redis | — |
| `CACHE_TTL_DEFAULT` | TTL кеша по умолчанию (сек) | `300` |
| `JWT_ACCESS_SECRET` | Секрет для access токенов | — |
| `JWT_REFRESH_SECRET` | Секрет для refresh токенов | — |
| `YANDEX_CLIENT_ID` | ID приложения Яндекс OAuth | — |
| `YANDEX_CLIENT_SECRET` | Секрет приложения Яндекс OAuth | — |
| `VK_CLIENT_ID` | ID приложения VK OAuth | — |
| `VK_CLIENT_SECRET` | Секрет приложения VK OAuth | — |

## 📚 API Документация

После запуска в режиме **development** доступны:

| Интерфейс | Адрес | Описание |
|-----------|-------|----------|
| Swagger UI | http://localhost:4200/docs | Интерактивная документация |
| ReDoc | http://localhost:4200/redoc | Альтернативная документация |
| OpenAPI JSON | http://localhost:4200/openapi.json | Спецификация в формате JSON |

> ⚠️ **В production режиме** (`NODE_ENV=production`) документация автоматически отключается.

## ✅ Особенности реализации

- ✅ Кеширование через Redis с паттерном Cache-Aside
- ✅ Явное управление ключами и TTL в сервисном слое
- ✅ Инвалидация кеша при всех операциях записи
- ✅ Хранение JTI Access токенов в Redis для мгновенного отзыва
- ✅ Graceful degradation при недоступности Redis
- ✅ Иерархические префиксы ключей (`wp:module:entity:id`)
- ✅ Валидация входящих данных через Pydantic
- ✅ JWT аутентификация через HttpOnly cookies
- ✅ OAuth 2.0 авторизация (Яндекс, VK)
- ✅ Пагинация, валидация, обработка ошибок
- ✅ Мягкое удаление (soft delete)
- ✅ Разделение документации по окружениям (dev / prod)

## 👥 Авторы

Разработано в рамках лабораторной работы по Web-технологиям.
