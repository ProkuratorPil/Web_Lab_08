"""
Сервис для отправки email через SMTP.
"""
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Сервис отправки электронной почты через SMTP."""

    def __init__(self):
        self._smtp_host: Optional[str] = None
        self._smtp_port: Optional[int] = None
        self._smtp_user: Optional[str] = None
        self._smtp_pass: Optional[str] = None
        self._smtp_from: Optional[str] = None
        self._smtp_secure: bool = True
        self._configured: bool = False

    def configure(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        from_addr: str,
        secure: bool = True,
    ) -> None:
        """Настраивает SMTP подключение."""
        self._smtp_host = host
        self._smtp_port = port
        self._smtp_user = user
        self._smtp_pass = password
        self._smtp_from = from_addr
        self._smtp_secure = secure
        self._configured = True
        logger.info(f"Email service configured (host={host}, port={port}, user={user}, secure={secure})")

    def validate_config(self) -> None:
        """Валидирует конфигурацию SMTP. При ошибке завершает приложение."""
        missing = []
        if not self._smtp_host:
            missing.append("SMTP_HOST")
        if not self._smtp_port:
            missing.append("SMTP_PORT")
        if not self._smtp_user:
            missing.append("SMTP_USER")
        if not self._smtp_pass:
            missing.append("SMTP_PASS")
        if not self._smtp_from:
            missing.append("SMTP_FROM")

        if missing:
            raise RuntimeError(
                f"SMTP configuration is incomplete. Missing required variables: {', '.join(missing)}"
            )
        logger.info("SMTP configuration validated successfully")

    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        """
        Отправляет email.

        Args:
            to: Адрес получателя
            subject: Тема письма
            html_body: HTML-содержимое письма
            text_body: Plain text содержимое (опционально)

        Returns:
            True если отправка успешна, False при ошибке
        """
        if not self._configured:
            logger.error("Email service is not configured")
            return False

        msg = MIMEMultipart("alternative")
        msg["From"] = self._smtp_from
        msg["To"] = to
        msg["Subject"] = subject

        # Plain text version (fallback)
        if text_body:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
        else:
            msg.attach(MIMEText(_strip_html(html_body), "plain", "utf-8"))

        # HTML version
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            use_tls = self._smtp_secure
            smtp = aiosmtplib.SMTP(
                hostname=self._smtp_host,
                port=self._smtp_port,
                use_tls=use_tls,
            )

            await smtp.connect()
            await smtp.login(self._smtp_user, self._smtp_pass)
            await smtp.send_message(msg)
            await smtp.quit()

            logger.info(f"Email sent successfully to {to}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return False

    async def send_welcome_email(self, to: str, display_name: str) -> bool:
        """
        Отправляет приветственное письмо новому пользователю.

        Args:
            to: Email получателя
            display_name: Отображаемое имя пользователя

        Returns:
            True если отправка успешна
        """
        subject = "Добро пожаловать!"
        display_name_display = display_name or "Пользователь"

        html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ padding: 20px; background: #f9f9f9; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ padding: 20px; text-align: center; color: #777; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Добро пожаловать!</h1>
        </div>
        <div class="content">
            <h2>Здравствуйте, {display_name_display}!</h2>
            <p>Благодарим вас за регистрацию в нашем сервисе. Ваш аккаунт был успешно создан.</p>
            <p>Теперь вы можете войти в систему и начать пользоваться всеми возможностями нашего сервиса.</p>
            <p style="text-align: center;">
                <a href="http://localhost:4200/login" class="button">Войти в систему</a>
            </p>
            <p>Если вы не регистрировались в нашем сервисе, просто проигнорируйте это письмо.</p>
            <p>С уважением,<br>Команда Lab Project</p>
        </div>
        <div class="footer">
            <p>&copy; 2026 Lab Project. Все права защищены.</p>
        </div>
    </div>
</body>
</html>"""

        text_body = f"""Здравствуйте, {display_name_display}!

Благодарим вас за регистрацию в нашем сервисе. Ваш аккаунт был успешно создан.

Теперь вы можете войти в систему и начать пользоваться всеми возможностями нашего сервиса.

Ссылка для входа: http://localhost:4200/login

Если вы не регистрировались в нашем сервисе, просто проигнорируйте это письмо.

С уважением,
Команда Lab Project"""

        return await self.send_email(
            to=to,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )


def _strip_html(html: str) -> str:
    """Простое удаление HTML-тегов из строки."""
    import re
    return re.sub(r"<[^>]+>", "", html).strip()


# Глобальный экземпляр сервиса email
email_service = EmailService()