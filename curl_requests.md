# Curl запросы для API

Базовый URL: `http://localhost:8000`

---

## AUTH

### POST /auth/register - Регистрация пользователя
```bash
curl --location 'http://localhost:8000/auth/register' \
--header 'Content-Type: application/json' \
--data-raw '{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "password123",
    "first_name": "Ivan",
    "last_name": "Ivanov",
    "phone": "+1234567890"
}'
```

### POST /auth/login - Вход пользователя
```bash
curl --location 'http://localhost:8000/auth/login' \
--header 'Content-Type: application/json' \
--data-raw '{
    "email": "newuser@example.com",
    "password": "password123"
}'
```

### GET /auth/whoami - Получить текущего пользователя
```bash
curl --location 'http://localhost:8000/auth/whoami' \
--header 'Authorization: Bearer YOUR_ACCESS_TOKEN'
```

### POST /auth/logout - Выход
```bash
curl --location --request POST 'http://localhost:8000/auth/logout' \
--header 'Authorization: Bearer YOUR_ACCESS_TOKEN'
```

---

## USERS

### POST /users/ - Создать пользователя (публичный)
```bash
curl --location 'http://localhost:8000/users/' \
--header 'Content-Type: application/json' \
--data-raw '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123",
    "first_name": "Ivan",
    "last_name": "Ivanov",
    "phone": "+1234567890"
}'
```

### GET /users/ - Получить список пользователей (защищённый)
```bash
curl --location 'http://localhost:8000/users/?page=1&limit=10' \
--header 'Authorization: Bearer YOUR_ACCESS_TOKEN'
```

### GET /users/{id} - Получить пользователя по ID (защищённый)
```bash
curl --location 'http://localhost:8000/users/USER_ID_HERE' \
--header 'Authorization: Bearer YOUR_ACCESS_TOKEN'
```

### PUT /users/{id} - Полное обновление пользователя (защищённый)
```bash
curl --location --request PUT 'http://localhost:8000/users/USER_ID_HERE' \
--header 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
--header 'Content-Type: application/json' \
--data-raw '{
    "username": "updatedusername",
    "email": "updated@example.com",
    "first_name": "Petr",
    "last_name": "Petrov",
    "phone": "+9876543210"
}'
```

### PATCH /users/{id} - Частичное обновление пользователя (защищённый)
```bash
curl --location --request PATCH 'http://localhost:8000/users/USER_ID_HERE' \
--header 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
--header 'Content-Type: application/json' \
--data-raw '{
    "first_name": "Sergey",
    "last_name": "Sergeev"
}'
```

### DELETE /users/{id} - Удалить пользователя (защищённый)
```bash
curl --location --request DELETE 'http://localhost:8000/users/USER_ID_HERE' \
--header 'Authorization: Bearer YOUR_ACCESS_TOKEN'
```

---

## HEALTH CHECK

### GET / - Корневой endpoint
```bash
curl --location 'http://localhost:8000/'
```

### GET /health - Проверка здоровья
```bash
curl --location 'http://localhost:8000/health'
```

---

# Postman Collection JSON

```json
{
    "info": {
        "name": "User & File Management API",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": [
        {
            "name": "Auth",
            "item": [
                {
                    "name": "Register",
                    "request": {
                        "method": "POST",
                        "url": "http://localhost:8000/auth/register",
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": "{\n    \"username\": \"newuser\",\n    \"email\": \"newuser@example.com\",\n    \"password\": \"password123\",\n    \"first_name\": \"Ivan\",\n    \"last_name\": \"Ivanov\",\n    \"phone\": \"+1234567890\"\n}"
                        }
                    }
                },
                {
                    "name": "Login",
                    "request": {
                        "method": "POST",
                        "url": "http://localhost:8000/auth/login",
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": "{\n    \"email\": \"newuser@example.com\",\n    \"password\": \"password123\"\n}"
                        }
                    }
                },
                {
                    "name": "Whoami",
                    "request": {
                        "method": "GET",
                        "url": "http://localhost:8000/auth/whoami",
                        "header": [
                            {
                                "key": "Authorization",
                                "value": "Bearer YOUR_ACCESS_TOKEN"
                            }
                        ]
                    }
                },
                {
                    "name": "Logout",
                    "request": {
                        "method": "POST",
                        "url": "http://localhost:8000/auth/logout",
                        "header": [
                            {
                                "key": "Authorization",
                                "value": "Bearer YOUR_ACCESS_TOKEN"
                            }
                        ]
                    }
                }
            ]
        },
        {
            "name": "Users",
            "item": [
                {
                    "name": "Create User",
                    "request": {
                        "method": "POST",
                        "url": "http://localhost:8000/users/",
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": "{\n    \"username\": \"testuser\",\n    \"email\": \"test@example.com\",\n    \"password\": \"password123\",\n    \"first_name\": \"Ivan\",\n    \"last_name\": \"Ivanov\",\n    \"phone\": \"+1234567890\"\n}"
                        }
                    }
                },
                {
                    "name": "Get Users",
                    "request": {
                        "method": "GET",
                        "url": {
                            "raw": "http://localhost:8000/users/?page=1&limit=10",
                            "query": [
                                {"key": "page", "value": "1"},
                                {"key": "limit", "value": "10"}
                            ]
                        },
                        "header": [
                            {
                                "key": "Authorization",
                                "value": "Bearer YOUR_ACCESS_TOKEN"
                            }
                        ]
                    }
                },
                {
                    "name": "Get User by ID",
                    "request": {
                        "method": "GET",
                        "url": "http://localhost:8000/users/USER_ID_HERE",
                        "header": [
                            {
                                "key": "Authorization",
                                "value": "Bearer YOUR_ACCESS_TOKEN"
                            }
                        ]
                    }
                },
                {
                    "name": "Update User (PUT)",
                    "request": {
                        "method": "PUT",
                        "url": "http://localhost:8000/users/USER_ID_HERE",
                        "header": [
                            {
                                "key": "Authorization",
                                "value": "Bearer YOUR_ACCESS_TOKEN"
                            },
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": "{\n    \"username\": \"updatedusername\",\n    \"email\": \"updated@example.com\",\n    \"first_name\": \"Petr\",\n    \"last_name\": \"Petrov\",\n    \"phone\": \"+9876543210\"\n}"
                        }
                    }
                },
                {
                    "name": "Update User (PATCH)",
                    "request": {
                        "method": "PATCH",
                        "url": "http://localhost:8000/users/USER_ID_HERE",
                        "header": [
                            {
                                "key": "Authorization",
                                "value": "Bearer YOUR_ACCESS_TOKEN"
                            },
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": "{\n    \"first_name\": \"Sergey\",\n    \"last_name\": \"Sergeev\"\n}"
                        }
                    }
                },
                {
                    "name": "Delete User",
                    "request": {
                        "method": "DELETE",
                        "url": "http://localhost:8000/users/USER_ID_HERE",
                        "header": [
                            {
                                "key": "Authorization",
                                "value": "Bearer YOUR_ACCESS_TOKEN"
                            }
                        ]
                    }
                }
            ]
        },
        {
            "name": "Health",
            "item": [
                {
                    "name": "Root",
                    "request": {
                        "method": "GET",
                        "url": "http://localhost:8000/"
                    }
                },
                {
                    "name": "Health Check",
                    "request": {
                        "method": "GET",
                        "url": "http://localhost:8000/health"
                    }
                }
            ]
        }
    ]
}