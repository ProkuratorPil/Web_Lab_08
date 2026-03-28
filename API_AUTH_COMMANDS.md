# curl команды для Windows PowerShell

## Регистрация пользователя
```powershell
curl.exe -X POST http://localhost:4200/auth/register -H "Content-Type: application/json" -d "{\`"username\`": \`"testuser\`", \`"email\`": \`"test@example.com\`", \`"password\`": \`"SecurePass123\`"}"
```

## Вход (получение токенов)
```powershell
curl.exe -X POST http://localhost:4200/auth/login -H "Content-Type: application/json" -d "{\`"email\`": \`"test@example.com\`", \`"password\`": \`"SecurePass123\`"}" -c cookies.txt
```

## Проверка профиля (whoami)
```powershell
curl.exe -X GET http://localhost:4200/auth/whoami -b cookies.txt
```

## Выход (logout)
```powershell
curl.exe -X POST http://localhost:4200/auth/logout -b cookies.txt
```

## Защищённый роут - Список пользователей
```powershell
curl.exe -X GET http://localhost:4200/users/ -b cookies.txt -L
```

## Обновление токенов (refresh)
```powershell
curl.exe -X POST http://localhost:4200/auth/refresh -b cookies.txt
```

## Выход со всех устройств
```powershell
curl.exe -X POST http://localhost:4200/auth/logout-all -b cookies.txt
```

---

## Вариант с использованием переменных (удобнее)

### Регистрация
```powershell
$body = @{
    username = "newuser"
    email = "new@example.com"
    password = "SecurePass123"
} | ConvertTo-Json

curl.exe -X POST http://localhost:4200/auth/register -H "Content-Type: application/json" -Body $body
```

### Вход
```powershell
$body = @{
    email = "test@example.com"
    password = "SecurePass123"
} | ConvertTo-Json

curl.exe -X POST http://localhost:4200/auth/login -H "Content-Type: application/json" -Body $body -c cookies.txt
```

### Проверка профиля
```powershell
curl.exe -X GET http://localhost:4200/auth/whoami -b cookies.txt
```

---

## Notes

- Ключ `-c cookies.txt` сохраняет cookies в файл
- Ключ `-b cookies.txt` отправляет cookies с запросом
- Ключ `-L` follows redirects
- Ключ `-H` добавляет заголовки
- Ключ `-X` указывает метод (GET, POST, etc.)
- В PowerShell используется обратный апостроф (`) для экранирования кавычек внутри строки