# Тестирование Redis-кеша (Windows CMD)

Предварительно убедитесь, что контейнеры запущены:

```cmd
docker compose up -d
```

---

## 1. Аутентификация (логин)

Сохраняет cookies в `cookies.txt`:

```cmd
curl -s -X POST "http://localhost:4200/auth/login" -H "Content-Type: application/json" -d "{\"email\":\"john.doe@example.com\",\"password\":\"SecurePassword123\"}" -c cookies.txt
```

Если логин не сработает, зарегистрируйтесь:

```cmd
curl -s -X POST "http://localhost:4200/auth/register" -H "Content-Type: application/json" -d "{\"username\":\"testuser\",\"email\":\"test@example.com\",\"password\":\"password123\",\"phone\":\"+79990001122\"}"
```

---

## 2. Cache Miss (первый запрос — данные из PostgreSQL)

```cmd
curl -s -X GET "http://localhost:4200/users/?page=1&limit=10" -b cookies.txt
```

---

## 3. Проверка ключа в Redis

```cmd
docker exec wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod get "wp:users:list:page:1:limit:10"
```

Ожидаемый результат: JSON-строка с массивом пользователей и total.

---

## 4. Проверка TTL ключа (оставшееся время жизни в секундах)

```cmd
docker exec wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod ttl "wp:users:list:page:1:limit:10"
```

Ожидаемый результат: число (например, `99`).

---

## 5. Cache Hit (второй запрос — ответ из Redis, без запроса к БД)

```cmd
curl -s -X GET "http://localhost:4200/users/?page=1&limit=10" -b cookies.txt
```

---

## 6. Поиск всех ключей `wp:users:*`

```cmd
docker exec wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod --scan --pattern "wp:users:*"
```

---

## 7. Размер ключа в байтах (STRLEN)

```cmd
docker exec wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod strlen "wp:users:list:page:1:limit:10"
```

---

## 8. Удаление ключа (инвалидация кеша)

```cmd
docker exec wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod del "wp:users:list:page:1:limit:10"
```

---

## 9. Проверка отсутствия ключа (должен вернуть `nil`)

```cmd
docker exec wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod get "wp:users:list:page:1:limit:10"
```

---

## 10. Мониторинг Redis в реальном времени

Выполните в **отдельном** терминале. Нажмите `Ctrl+C` для остановки.

```cmd
docker exec -it wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod MONITOR
```

---

## 11. Общая информация о Redis (keyspace)

```cmd
docker exec wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod info keyspace
```

---

## 12. Проверка доступности Redis (PING)

```cmd
docker exec wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod ping
```

---

## 13. Просмотр JTI-сессий (мгновенный отзыв токенов)

После логина в Redis сохраняются ключи вида `wp:auth:user:{user_id}:access:{jti}`.  
Найти все активные сессии пользователя (замените `*` на `user_id` если известен):

```cmd
docker exec wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod --scan --pattern "wp:auth:user:*:access:*"
```

Посмотреть значение конкретного JTI:

```cmd
docker exec wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod get "wp:auth:user:4e0ce7ca-040a-4282-8074-09c3b61e3c64:access:7b0e..."
```

---

## 14. Инвалидация всех сессий пользователя (logout-all)

Удалить все JTI одного пользователя:

```cmd
docker exec wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod --scan --pattern "wp:auth:user:4e0ce7ca-040a-4282-8074-09c3b61e3c64:access:*" | xargs docker exec wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod unlink
```

Или напрямую через API:

```cmd
curl -s -X POST "http://localhost:4200/auth/logout-all" -b cookies.txt
```

---

## 15. Инвалидация кеша профиля

```cmd
docker exec wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod del "wp:users:profile:4e0ce7ca-040a-4282-8074-09c3b61e3c64"
```

---

## 16. Список всех ключей в Redis

```cmd
docker exec wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod keys "*"
```

> **Внимание:** `keys *` — тяжёлая операция. В продакшене используйте `--scan`.

---

## 17. Подсчёт ключей по паттерну

```cmd
docker exec wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod --scan --pattern "wp:users:*" | find /c /v ""
```

---

## 18. Очистка всей БД Redis (полный сброс кеша)

```cmd
docker exec wp_labs_redis redis-cli --pass redis_secure_password_change_in_prod flushdb
```

---

## GUI-приложения для просмотра Redis

| Приложение | Платформа | Установка |
|---|---|---|
| **Redis Insight** (официальный) | Windows / macOS / Linux | [Скачать](https://redis.io/insight/) |
| **Another Redis Desktop Manager** | Windows / macOS / Linux | [GitHub](https://github.com/qishibo/AnotherRedisDesktopManager) |
| **Medis** | macOS | [Скачать](https://getmedis.com/) |
| **Redis Commander** (Web) | Любая | `docker run -p 8081:8081 rediscommander/redis-commander --redis-host localhost --redis-password redis_secure_password_change_in_prod` |

### Подключение через Redis Insight

1. Запустите Redis Insight
2. **Add Redis Database**
3. **Host**: `localhost`
4. **Port**: `6379`
5. **Password**: `redis_secure_password_change_in_prod`
6. **Test Connection** → **Add Database**

В Redis Insight вы сможете:
- Видеть все ключи и их структуру
- Просматривать TTL в реальном времени
- Редактировать/удалять ключи
- Смотреть статистику сервера
- Использовать CLI внутри GUI

---

## Примечание

Пароль `redis_secure_password_change_in_prod` указан в `.env` и `docker-compose.yml`. Если вы изменили `REDIS_PASSWORD`, замените его во всех командах.
