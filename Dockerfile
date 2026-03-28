FROM python:3.12-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --default-timeout=100 --retries 5 --no-cache-dir -r requirements.txt

COPY web_lab1 .

# Пропускаем alembic - используем init.sql для создания таблиц
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "4200"]