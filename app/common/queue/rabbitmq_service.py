"""
Сервис для работы с RabbitMQ.
Реализует подключение, публикацию, потребление сообщений с гарантиями доставки.
"""
import json
import logging
from typing import Optional, Callable, Awaitable, Any
from uuid import UUID

import aio_pika
from aio_pika import Message, DeliveryMode, Channel, Connection
from aio_pika.abc import AbstractIncomingMessage

from app.core.config import settings

logger = logging.getLogger(__name__)

MessageHandler = Callable[[AbstractIncomingMessage], Awaitable[None]]


class RabbitMQService:
    """Сервис-абстракция для работы с RabbitMQ."""

    def __init__(self):
        self._connection: Optional[Connection] = None
        self._channel: Optional[Channel] = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._channel is not None and not self._channel.is_closed

    async def connect(self) -> None:
        """Устанавливает соединение с RabbitMQ."""
        if self.is_connected:
            return

        try:
            host = settings.RABBITMQ_HOST
            port = settings.RABBITMQ_PORT
            user = settings.RABBITMQ_USER
            pwd = settings.RABBITMQ_PASS

            self._connection = await aio_pika.connect_robust(
                host=host,
                port=port,
                login=user,
                password=pwd,
                heartbeat=60,
            )
            self._channel = await self._connection.channel()
            self._connected = True
            logger.info("RabbitMQ connection established successfully")
        except Exception as e:
            self._connected = False
            self._connection = None
            self._channel = None
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def disconnect(self) -> None:
        """Закрывает соединение с RabbitMQ."""
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        self._connected = False
        self._channel = None
        self._connection = None
        logger.info("RabbitMQ connection closed")

    async def declare_exchange(self, name: str, exchange_type: str = "direct", durable: bool = True) -> None:
        """Декларирует обменник."""
        if not self.is_connected:
            await self.connect()
        await self._channel.declare_exchange(name, type=exchange_type, durable=durable)
        logger.info(f"Exchange '{name}' declared (type={exchange_type}, durable={durable})")

    async def declare_queue(
        self,
        name: str,
        durable: bool = True,
        dead_letter_exchange: Optional[str] = None,
        dead_letter_routing_key: Optional[str] = None,
    ) -> None:
        """Декларирует очередь с опциональной DLQ настройкой."""
        if not self.is_connected:
            await self.connect()

        arguments = {}
        if dead_letter_exchange:
            arguments["x-dead-letter-exchange"] = dead_letter_exchange
        if dead_letter_routing_key:
            arguments["x-dead-letter-routing-key"] = dead_letter_routing_key

        await self._channel.declare_queue(name, durable=durable, arguments=arguments)
        logger.info(f"Queue '{name}' declared (durable={durable}, dlx={dead_letter_exchange})")

    async def bind_queue(self, queue_name: str, exchange_name: str, routing_key: str) -> None:
        """Привязывает очередь к обменнику с routing key."""
        if not self.is_connected:
            await self.connect()
        queue = await self._channel.get_queue(queue_name)
        exchange = await self._channel.get_exchange(exchange_name)
        await queue.bind(exchange, routing_key=routing_key)
        logger.info(f"Queue '{queue_name}' bound to '{exchange_name}' with routing key '{routing_key}'")

    async def publish(
        self,
        exchange: str,
        routing_key: str,
        payload: dict[str, Any],
        persistent: bool = True,
    ) -> None:
        """
        Публикует сообщение в обменник.
        
        Args:
            exchange: Имя обменника
            routing_key: Ключ маршрутизации
            payload: Тело сообщения (будет сериализовано в JSON)
            persistent: Флаг постоянства сообщения (запись на диск)
        """
        if not self.is_connected:
            await self.connect()

        body = json.dumps(payload, default=str).encode("utf-8")
        delivery_mode = DeliveryMode.PERSISTENT if persistent else DeliveryMode.NOT_PERSISTENT

        message = Message(
            body=body,
            delivery_mode=delivery_mode,
            content_type="application/json",
        )

        exchange_obj = await self._channel.get_exchange(exchange)
        await exchange_obj.publish(message, routing_key=routing_key)
        logger.debug(f"Message published to '{exchange}' with routing key '{routing_key}'")

    async def consume(
        self,
        queue: str,
        handler: MessageHandler,
        prefetch_count: int = 1,
    ) -> None:
        """
        Начинает потребление сообщений из очереди.
        
        Args:
            queue: Имя очереди
            handler: Асинхронная функция-обработчик сообщения
            prefetch_count: Количество сообщений, выдаваемых за раз
        """
        if not self.is_connected:
            await self.connect()

        await self._channel.set_qos(prefetch_count=prefetch_count)
        queue_obj = await self._channel.get_queue(queue)
        await queue_obj.consume(handler)
        logger.info(f"Consumer started on queue '{queue}' (prefetch={prefetch_count})")

    async def ack(self, message: AbstractIncomingMessage) -> None:
        """Подтверждает успешную обработку сообщения."""
        if message and not message.processed:
            await message.ack()
            logger.debug("Message acknowledged")

    async def nack(self, message: AbstractIncomingMessage, requeue: bool = False) -> None:
        """Отклоняет сообщение. С requeue=True сообщение возвращается в очередь."""
        if message and not message.processed:
            await message.nack(requeue=requeue)
            logger.debug(f"Message nacked (requeue={requeue})")


# Глобальный экземпляр сервиса RabbitMQ
rabbitmq_service = RabbitMQService()