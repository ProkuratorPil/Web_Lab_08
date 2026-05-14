# Лабораторный проект Web-программирование (Lab Project API)

API для лабораторных работ №2-№8 по веб-программированию.
Реализовано на **FastAPI** с **MongoDB** (Beanie ODM), **Redis** (кеширование + JTI revocation), **MinIO** (объектное хранилище), **JWT** (access + refresh токены), **OAuth 2.0** (Яндекс, VK), **RabbitMQ** (асинхронная обработка событий), **SMTP** (отправка email).

## Функциональность

### Аутентификация и авторизация
- Регистрация с валидацией пароля (заглавные, строчные, цифры)
- Вход с установкой HttpOnly cookies (access_token, refresh_token)
- Refresh токенов (rotation)
- Выход из текущей и всех сессий
- OAuth 2.0 через Яндекс и VK (Authorization Code Grant)
- Soft Delete для пользователей
- Кеширование профиля в Redis

### Управление пользователями
- CRUD пользователей (Create, Read, Update, Delete)
- Кеширование списков и профилей в Redis
- Пагинация

### Файлы (MinIO Object Storage)
- **POST /files** — Загрузка файла (multipart/form-data) в MinIO с потоковой передачей
- **GET /files** — Список файлов пользователя (пагинированный)
- **GET /files/{file_id}** — Скачивание файла через StreamingResponse
- **DELETE /files/{file_id}** — Удаление файла (hard delete из MinIO + soft delete в MongoDB)
- Валидация MIME-типов и размеров файлов (10 MB макс.)
- Метаданные файлов хранятся в MongoDB, файлы — в MinIO
- Кеширование метаданных файлов в Redis (TTL: 300 сек)

### Профиль и Аватар
- **GET /users/profile** — Получение профиля текущего пользователя
- **POST /users/profile** — Обновление профиля (display_name, bio, avatar_file_id)
- Проверка владения файлом при установке аватара
- Кеширование профиля в Redis

### Асинхронная обработка событий (RabbitMQ) — ЛР №8
- При регистрации пользователя публикуется событие `user.registered` в RabbitMQ
- Фоновый consumer отправляет приветственное email через SMTP
- Механизм повторных попыток (до 3 раз) при временных ошибках SMTP
- Dead Letter Queue для сообщений, не обработанных после 3 попыток
- Идемпотентность обработки через Redis (eventId хранится 24 часа)
- Гарантированная доставка: persistent messages + acknowledgements

## Технологический стек

- **FastAPI** (async Python web framework)
- **MongoDB 7** (NoSQL база данных)
- **Beanie ODM** (async MongoDB ODM)
- **Redis 7** (кеширование, JTI revocation, идемпотентность eventId)
- **RabbitMQ 3.12** (брокер сообщений, Management Plugin)
- **SMTP** (отправка email через aiosmtplib)
- **MinIO** (объектное хранилище, S3-совместимое)
- **JWT** (access + refresh токены)
- **OAuth 2.0** (Яндекс, VK)
- **Docker** + **Docker Compose**

## Быстрый старт

### Требования

- Docker и Docker Compose
- Git
- Аккаунт в почтовом сервисе с поддержкой SMTP (Yandex, Gmail или аналог)

### Установка и запуск

```bash
# 1. Клонируйте репозиторий
git clone <repository-url>
cd WB_Lab_5

# 2. Создайте файл .env на основе .env.example
cp .env.example .env
# Отредактируйте .env — укажите свои SMTP-данные:
#   SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM

# 3. Запустите все сервисы
docker-compose up --build
```

### Доступные сервисы

| Сервис | URL | Описание |
|--------|-----|----------|
| API | http://localhost:4200 | FastAPI приложение |
| Swagger UI | http://localhost:4200/docs | Документация API |
| ReDoc | http://localhost:4200/redoc | Альтернативная документация |
| RabbitMQ Management | http://localhost:15672 | Management UI очередей |
| MinIO API | http://localhost:9000 | S3-совместимый API |
| MinIO Console | http://localhost:9001 | Web-интерфейс MinIO |
| Redis Insight | http://localhost:5540 | Web-интерфейс Redis |

### RabbitMQ Management UI

1. Откройте http://localhost:15672
2. Логин: `student`, Пароль: `student_secure_rabbit_pass_change_in_prod` (или из .env)
3. Вкладка **Queues** — просмотр очередей `wp.auth.user.registered` и `wp.auth.user.registered.dlq`
4. Вкладка **Exchanges** — просмотр `app.events` (direct) и `app.dlx` (direct)

### MinIO Console

1. Откройте http://localhost:9001
2. Войдите с логином: `minio_admin`, пароль: `minio_secure_password`
3. Создайте bucket: `wp-labs-files` (если не создался автоматически)

## API Endpoints

### Аутентификация

| Метод | URI | Описание | Доступ |
|-------|-----|----------|--------|
| POST | /auth/register | Регистрация (+ публикация события в RabbitMQ) | Public |
| POST | /auth/login | Вход | Public |
| POST | /auth/refresh | Обновление токенов | Cookie |
| POST | /auth/logout | Выход | Private |
| POST | /auth/logout-all | Выход из всех сессий | Private |
| GET | /auth/whoami | Текущий пользователь | Private |
| GET | /auth/oauth/{provider} | OAuth авторизация | Public |
| GET | /auth/oauth/{provider}/callback | OAuth callback | Public |
| POST | /auth/forgot-password | Запрос сброса пароля | Public |
| POST | /auth/reset-password | Сброс пароля | Public |

### Пользователи

| Метод | URI | Описание | Доступ |
|-------|-----|----------|--------|
| POST | /users | Создать | Public |
| GET | /users | Список | Private |
| GET | /users/{user_id} | По ID | Private |
| PUT | /users/{user_id} | Обновить | Owner |
| PATCH | /users/{user_id} | Частичное обновление | Owner |
| DELETE | /users/{user_id} | Удалить | Owner |
| GET | /users/profile | Профиль | Own |
| POST | /users/profile | Обновить профиль | Own |

### Файлы

| Метод | URI | Описание | Статус успеха | Доступ |
|-------|-----|----------|---------------|--------|
| POST | /files | Загрузка файла (multipart/form-data) | 201 Created | Private |
| GET | /files | Список файлов | 200 OK | Owner |
| GET | /files/{file_id} | Скачивание файла | 200 OK | Owner |
| DELETE | /files/{file_id} | Удаление файла | 204 No Content | Owner |

### Системные

| Метод | URI | Описание |
|-------|-----|----------|
| GET | / | Приветствие |
| GET | /health | Healthcheck |

## Асинхронная обработка событий (RabbitMQ)

### Архитектура

```
                    ┌─────────────────────────────────────────────┐
                    │              RabbitMQ 3.12                  │
                    │                                             │
                    │  Exchange: app.events (direct, durable)      │
                    │       routing_key: user.registered           │
                    │                    │                         │
                    │                    ▼                         │
                    │  Queue: wp.auth.user.registered (durable)    │
                    │       ┌─ x-dead-letter-exchange: app.dlx     │
                    │       └─ x-dead-letter-routing-key: user.reg│
                    │                    │                         │
                    │                    ▼                         │
                    │  Exchange: app.dlx (direct, durable)         │
                    │                    │                         │
                    │                    ▼                         │
                    │  Queue: wp.auth.user.registered.dlq (DLQ)    │
                    └─────────────────────────────────────────────┘
                                │                        ▲
                                │ consume                │
                                ▼                        │
                    ┌──────────────────────┐              │
                    │  Background Consumer  │──retry(3)───┘
                    │  (в том же процессе)  │
                    │                      │
                    │  1. Десериализация    │
                    │  2. Проверка eventId  │
                    │  3. SMTP отправка     │
                    │  4. ack/nack          │
                    └──────────────────────┘
```

### Схема взаимодействия

```
Client          HTTP Server      Auth Service     Queue Module      RabbitMQ       Consumer        SMTP
  │                  │                │                │              │              │              │
  │  POST /register  │                │                │              │              │              │
  │─────────────────►│                │                │              │              │              │
  │                  │  Валидация+БД  │                │              │              │              │
  │                  │───────────────►│                │              │              │              │
  │                  │                │  Сохранение     │              │              │              │
  │                  │◄───────────────│                │              │              │              │
  │                  │                │                │              │              │              │
  │                  │  publish()     │                │              │              │              │
  │                  │──────────────────────────────────────────────►│              │              │
  │                  │                │                │              │              │              │
  │  201 Created     │                │                │              │  Доставка    │              │
  │◄─────────────────│                │                │              │─────────────►│              │
  │                                                                  │              │              │
  │                                                                  │              │send_email()  │
  │                                                                  │              │─────────────►│
  │                                                                  │              │              │
  │                                                                  │              │◄────250 OK───│
  │                                                                  │              │              │
  │                                                                  │◄──ack()──────│              │
```

### Реализованные очереди и события

| Очередь | Exchange | Routing Key | Назначение |
|---------|----------|-------------|------------|
| `wp.auth.user.registered` | `app.events` (direct) | `user.registered` | Публикация события регистрации |
| `wp.auth.user.registered.dlq` | `app.dlx` (direct) | `user.registered` | Dead Letter Queue для необработанных |

#### Формат сообщения

```json
{
  "eventId": "uuid",
  "eventType": "user.registered",
  "timestamp": "2026-04-14T10:30:00Z",
  "payload": {
    "userId": "uuid",
    "email": "user@example.com",
    "displayName": "user"
  },
  "metadata": {
    "attempt": 1,
    "sourceService": "auth-service"
  }
}
```

**Важно:** В сообщениях не передаются пароли, хеши, токены или другие чувствительные данные.

### Механизм повторных попыток

1. При неудачной отправке email consumer отправляет **nack с requeue: true**
2. Перед повторной публикацией поле `metadata.attempt` увеличивается на 1
3. Если `attempt >= 3` — сообщение отправляется в Dead Letter Queue (`wp.auth.user.registered.dlq`)
4. В Redis хранятся `eventId` обработанных событий (TTL: 24 часа) для идемпотентности

### Dead Letter Queue

- Неудачные сообщения (после 3 попыток) перенаправляются в очередь `wp.auth.user.registered.dlq`
- DLQ настраивается через параметры `x-dead-letter-exchange` и `x-dead-letter-routing-key`
- Сообщения в DLQ можно просмотреть в RabbitMQ Management UI и повторно обработать при необходимости

### Идемпотентность

- Каждое событие имеет уникальный `eventId` (UUID)
- Consumer проверяет в Redis, не было ли событие уже обработано
- Если `eventId` найден — сообщение подтверждается (ack) без выполнения действий
- Обработанные `eventId` хранятся в Redis с TTL 24 часа (ключи: `wp:events:processed:{eventId}`)

## Проверка работы RabbitMQ

### 1. Тестирование публикации событий

Выполните регистрацию нового пользователя:

```bash
curl -X POST http://localhost:4200/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser_rabbit",
    "email": "your_email@example.com",
    "password": "TestPass123"
  }'
```

Ожидаемый ответ: `201 Created` с данными пользователя.

### 2. Проверка через RabbitMQ Management UI

1. Откройте http://localhost:15672 (логин: `student`, пароль: из .env)
2. Перейдите во вкладку **Queues**
3. Найдите очередь `wp.auth.user.registered`
4. Проверьте:
   - **Ready**: количество сообщений, готовых к обработке
   - **Unacked**: сообщения в процессе обработки
   - **Total**: общее количество
5. Если consumer запущен и SMTP настроен корректно — очередь будет пуста
6. Если consumer не может отправить email — сообщения будут накапливаться

### 3. Проверка Dead Letter Queue

Чтобы проверить механизм DLQ:

1. Укажите неверные SMTP-данные в .env (например, `SMTP_PASS=wrong_password`)
2. Перезапустите приложение: `docker-compose up --build`
3. Выполните регистрацию нескольких пользователей (команда из п.1)
4. В RabbitMQ Management UI:
   - Наблюдайте попытки обработки (сообщения будут возвращаться в очередь)
   - После 3 попыток сообщения должны появиться в `wp.auth.user.registered.dlq`

### 4. Проверка идемпотентности

Можно проверить вручную, опубликовав сообщение с одинаковым `eventId`:

```bash
# Через API публикуется автоматически, но для теста можно отправить напрямую
# (через Management UI → Queues → Publish message)
# При повторной отправке с тем же eventId письмо будет отправлено только один раз
```

### 5. Просмотр логов consumer

```bash
docker-compose logs app | grep -i "rabbitmq\|email\|event\|message"
```

Успешная отправка:
```
INFO ... Received event: user.registered (eventId=..., attempt=1)
INFO ... Email sent successfully to ...
INFO ... Event ... processed successfully
```

Ошибка и retry:
```
WARN ... Retry attempt 1/3 for event ...
INFO ... Event ... re-published for retry (attempt 2)
```

После 3 попыток:
```
ERROR ... Max retry attempts reached for event ... (3/3). Sending to DLQ.
```

## Переменные окружения (.env)

```env
# MongoDB
DB_USER=student
DB_PASSWORD=student_secure_password
DB_NAME=wp_labs
MONGO_URI="mongodb://student:student_secure_password@mongo:27017/wp_labs?authSource=admin"

# Application
PORT=4200
NODE_ENV=development

# JWT
JWT_ACCESS_SECRET=your_access_secret_key
JWT_REFRESH_SECRET=your_refresh_secret_key
JWT_ACCESS_EXPIRATION=15m
JWT_REFRESH_EXPIRATION=7d

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis_secure_password_change_in_prod
CACHE_TTL_DEFAULT=300

# RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=student
RABBITMQ_PASS=student_secure_rabbit_pass_change_in_prod

# Queue names (точечная нотация)
QUEUE_USER_REGISTERED=wp.auth.user.registered

# SMTP конфигурация
SMTP_HOST=smtp.yandex.ru
SMTP_PORT=465
SMTP_USER=your_email@yandex.ru
SMTP_PASS=your_app_password
SMTP_FROM=your_email@yandex.ru
SMTP_SECURE=true

# Yandex OAuth
YANDEX_CLIENT_ID=
YANDEX_CLIENT_SECRET=
YANDEX_CALLBACK_URL=http://localhost:4200/auth/oauth/yandex/callback

# VK OAuth
VK_CLIENT_ID=
VK_CLIENT_SECRET=
VK_CALLBACK_URL=http://localhost:4200/auth/oauth/vk/callback

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minio_admin
MINIO_SECRET_KEY=minio_secure_password
MINIO_BUCKET=wp-labs-files
MINIO_USE_SSL=false
MAX_FILE_SIZE=10485760
```

## Архитектура

### Модульная структура

```
app/
├── api/            # Альтернативные роутеры
├── common/
│   └── queue/      # RabbitMQ модуль (rabbitmq_service, consumer)
├── core/           # Ядро: config, database, dependencies, cache, jwt, security, oauth
├── crud/           # CRUD операции (file_crud, token_crud, book.py - user_crud)
├── models/         # Beanie ODM документы (user, token, uploaded_file)
├── routers/        # Роутеры FastAPI (auth, user, file)
├── schemas/        # Pydantic схемы (auth, common, file, user)
└── services/       # Бизнес-логика (user_service, file_service, minio_service, email_service)
```

### Поток загрузки файла (Streaming)

```
Client → POST /files (multipart/form-data)
  → FastAPI получает UploadFile
  → MinioService: потоковая загрузка (put_object)
  → MongoDB: сохранение метаданных
  → Redis: инвалидация кеша
  → Response: 201 + метаданные
```

### Поток скачивания файла (Streaming)

```
Client → GET /files/{file_id}
  → Проверка владения (file.user_id == current_user.id)
  → Redis: проверка кеша метаданных
  → MinioService: get_file_stream
  → StreamingResponse (32KB chunks)
  → Заголовки: Content-Type, Content-Disposition, Content-Length
```

### Поток асинхронной отправки email (RabbitMQ)

```
Client → POST /auth/register (синхронно)
  → регистрация в БД
  → publish() → exchange: app.events, routing_key: user.registered
  → 201 Created (мгновенный ответ)

RabbitMQ (асинхронно):
  → consumer получает сообщение из wp.auth.user.registered
  → проверка идемпотентности (eventId в Redis)
  → SMTP отправка приветственного email
  → ack при успехе / nack + retry при ошибке
  → после 3 неудач → Dead Letter Queue
```

## Кеширование

### Ключи Redis

- `wp:auth:user:{user_id}:access:{jti}` — JTI для мгновенного отзыва токенов
- `wp:users:detail:{user_id}` — Детали пользователя
- `wp:users:profile:{user_id}` — Профиль пользователя
- `wp:users:list:*` — Списки пользователей
- `wp:files:{file_id}:meta` — Метаданные файла
- `wp:files:list:{user_id}:*` — Списки файлов пользователя
- `wp:events:processed:{eventId}` — Идемпотентность обработки событий (TTL: 24 часа)

### TTL по умолчанию: 300 секунд
### Инвалидация: при создании, обновлении, удалении

## Безопасность

- Пароли хешируются через bcrypt/pbkdf2_sha256
- Токены хранятся в HttpOnly cookies (защита от XSS)
- JTI (JWT ID) для мгновенного отзыва токенов через Redis
- Валидация MIME-типов при загрузке файлов
- Ограничение размера файлов (10 MB)
- Проверка владения файлами
- Soft Delete для пользователей и файлов
- Чувствительные данные в .env
- Подключение к RabbitMQ защищено паролем (не guest/guest)
- В сообщениях RabbitMQ не передаются пароли, хеши, токены
- SMTP-credentials не логируются и не передаются в сообщениях
