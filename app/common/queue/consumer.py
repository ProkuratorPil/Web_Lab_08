"""
Consumer для обработки сообщений из очередей RabbitMQ.
Реализует механизмы повторных попыток, DLQ и идемпотентность.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from aio_pika.abc import AbstractIncomingMessage

from app.common.queue.rabbitmq_service import rabbitmq_service, MessageHandler
from app.core.config import settings
from app.core.cache import cache_service
from app.services.email_service import email_service

logger = logging.getLogger(__name__)

# Максимальное количество попыток обработки
MAX_RETRY_ATTEMPTS = 3

# TTL для хранения обработанных eventId (24 часа)
EVENT_TTL_SECONDS = 86400


async def setup_rabbitmq_infrastructure() -> None:
    """
    Декларирует все необходимые сущности RabbitMQ при старте приложения:
    - Exchange app.events (direct, durable)
    - Exchange app.dlx (direct, durable) - для dead letter
    - Queue wp.auth.user.registered (durable, с DLX на app.dlx)
    - Queue wp.auth.user.registered.dlq (durable)
    - Bindings
    """
    # Основной обменник событий
    await rabbitmq_service.declare_exchange("app.events", exchange_type="direct", durable=True)

    # Dead Letter Exchange
    await rabbitmq_service.declare_exchange("app.dlx", exchange_type="direct", durable=True)

    # Основная очередь для событий регистрации с DLQ настройкой
    await rabbitmq_service.declare_queue(
        "wp.auth.user.registered",
        durable=True,
        dead_letter_exchange="app.dlx",
        dead_letter_routing_key="user.registered",
    )

    # Dead Letter Queue
    await rabbitmq_service.declare_queue(
        "wp.auth.user.registered.dlq",
        durable=True,
    )

    # Bindings
    await rabbitmq_service.bind_queue(
        "wp.auth.user.registered", "app.events", "user.registered"
    )
    await rabbitmq_service.bind_queue(
        "wp.auth.user.registered.dlq", "app.dlx", "user.registered"
    )

    logger.info("RabbitMQ infrastructure declared successfully")


async def _is_event_processed(event_id: str) -> bool:
    """
    Проверяет, было ли событие уже обработано (идемпотентность).
    Использует Redis для хранения обработанных eventId с TTL 24 часа.
    """
    cache_key = f"wp:events:processed:{event_id}"
    result = cache_service.get(cache_key)
    return result is not None


async def _mark_event_processed(event_id: str) -> None:
    """
    Отмечает событие как обработанное в Redis с TTL 24 часа.
    """
    cache_key = f"wp:events:processed:{event_id}"
    cache_service.set(cache_key, True, ttl=EVENT_TTL_SECONDS)


async def handle_user_registered(message: AbstractIncomingMessage) -> None:
    """
    Обработчик событий регистрации пользователя.
    Отправляет приветственное email с механизмом retry и DLQ.
    """
    try:
        # Десериализация сообщения
        body = message.body.decode("utf-8")
        data = json.loads(body)

        event_id = data.get("eventId")
        event_type = data.get("eventType")
        timestamp = data.get("timestamp")
        payload = data.get("payload", {})
        metadata = data.get("metadata", {})

        email = payload.get("email")
        display_name = payload.get("displayName", "")
        attempt = metadata.get("attempt", 1)

        if not event_id or not email:
            logger.error(f"Invalid message: missing eventId or email. eventId={event_id}")
            await rabbitmq_service.nack(message, requeue=False)
            return

        logger.info(
            f"Received event: {event_type} (eventId={event_id}, attempt={attempt})"
        )

        # Проверка идемпотентности
        if await _is_event_processed(event_id):
            logger.info(f"Event {event_id} already processed, acknowledging")
            await rabbitmq_service.ack(message)
            return

        # Отправка приветственного email
        success = await email_service.send_welcome_email(
            to=email,
            display_name=display_name,
        )

        if success:
            # Помечаем событие как обработанное
            await _mark_event_processed(event_id)
            await rabbitmq_service.ack(message)
            logger.info(f"Event {event_id} processed successfully")
        else:
            # Ошибка отправки email - повторная попытка или DLQ
            if attempt >= MAX_RETRY_ATTEMPTS:
                logger.error(
                    f"Max retry attempts reached for event {event_id} "
                    f"({attempt}/{MAX_RETRY_ATTEMPTS}). Sending to DLQ."
                )
                await rabbitmq_service.nack(message, requeue=False)
            else:
                logger.warning(
                    f"Retry attempt {attempt}/{MAX_RETRY_ATTEMPTS} for event {event_id}"
                )
                # Обновляем количество попыток и отправляем обратно в очередь
                # Так как aio-pika не позволяет изменять сообщение, мы повторно публикуем
                data["metadata"]["attempt"] = attempt + 1
                await rabbitmq_service.publish(
                    exchange="app.events",
                    routing_key="user.registered",
                    payload=data,
                    persistent=True,
                )
                await rabbitmq_service.ack(message)
                logger.info(f"Event {event_id} re-published for retry (attempt {attempt + 1})")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode message JSON: {e}")
        await rabbitmq_service.nack(message, requeue=False)
    except Exception as e:
        logger.error(f"Critical error processing message: {e}", exc_info=True)
        await rabbitmq_service.nack(message, requeue=False)


async def start_consumer() -> None:
    """
    Инициализирует инфраструктуру RabbitMQ и запускает consumer.
    Вызывается при старте приложения.
    """
    try:
        await setup_rabbitmq_infrastructure()
        await rabbitmq_service.consume(
            queue="wp.auth.user.registered",
            handler=handle_user_registered,
            prefetch_count=1,
        )
        logger.info("RabbitMQ consumer started successfully")
    except Exception as e:
        logger.error(f"Failed to start RabbitMQ consumer: {e}")
        raise


async def stop_consumer() -> None:
    """Останавливает consumer и закрывает соединение с RabbitMQ."""
    try:
        await rabbitmq_service.disconnect()
        logger.info("RabbitMQ consumer stopped")
    except Exception as e:
        logger.error(f"Error stopping RabbitMQ consumer: {e}")