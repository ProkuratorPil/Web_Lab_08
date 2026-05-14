from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Environment
    NODE_ENV: str = "development"

    # MongoDB
    MONGO_URI: str = "mongodb://student:student_secure_password@localhost:27017/wp_labs?authSource=admin"
    DB_NAME: str = "wp_labs"
    PORT: int = 8000

    # JWT Secrets
    JWT_ACCESS_SECRET: str = "ba55f4e67c736521ae68caa5b307a2a0838e13193b7a0dbb87f31261aadceaab"
    JWT_REFRESH_SECRET: str = "c719a22d50a965ee222bca0c30cfcfe7f330a70e8cf7705c3fa2511f9389d38a"
    JWT_ACCESS_EXPIRATION: str = "15m"
    JWT_REFRESH_EXPIRATION: str = "7d"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    CACHE_TTL_DEFAULT: int = 300

    # Yandex OAuth
    YANDEX_CLIENT_ID: str = "aef65f68dbaf46a0a0f2af20ce216d72"
    YANDEX_CLIENT_SECRET: str = "daa09f23542b437fb0fced37249809a9"
    YANDEX_CALLBACK_URL: str = "http://localhost:8000/auth/oauth/yandex/callback"

    # VK OAuth
    VK_CLIENT_ID: str = "7890123"
    VK_CLIENT_SECRET: str = "your_vk_client_secret_here"
    VK_CALLBACK_URL: str = "http://localhost:8000/auth/oauth/vk/callback"

    # RabbitMQ
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "student"
    RABBITMQ_PASS: str = "student_secure_rabbit_pass_change_in_prod"

    # Queue names (точечная нотация)
    QUEUE_USER_REGISTERED: str = "wp.auth.user.registered"

    # SMTP
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = ""
    SMTP_SECURE: bool = True

    # MinIO
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minio_admin"
    MINIO_SECRET_KEY: str = "minio_secure_password"
    MINIO_BUCKET: str = "wp-labs-files"
    MINIO_USE_SSL: bool = False
    MAX_FILE_SIZE: int = 10485760  # 10 MB

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


settings = Settings()