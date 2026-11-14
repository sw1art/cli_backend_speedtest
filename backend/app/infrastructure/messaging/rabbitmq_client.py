"""RabbitMQ adapter implemented with aio-pika.

The main queue is durable. A companion retry queue is declared with a
dead-letter exchange pointing back at the main queue, so messages published to
the retry queue with a per-message TTL are automatically redelivered to the main
queue after the delay (the standard RabbitMQ retry pattern).
"""
from __future__ import annotations

import json
from typing import AsyncIterator, Optional
from uuid import UUID

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from ...application.exceptions import MessagePublishError
from ...application.interfaces.message_publisher import MessagePublisher


class RabbitMQClient(MessagePublisher):
    def __init__(
        self,
        url: str,
        queue_name: str = "download_tasks",
        retry_queue_name: str = "download_tasks.retry",
    ) -> None:
        self._url = url
        self._queue_name = queue_name
        self._retry_queue_name = retry_queue_name
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None
        self._queue = None
        self._retry_queue = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=1)

        retry_arguments = {
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": self._queue_name,
        }
        self._retry_queue = await self._channel.declare_queue(
            self._retry_queue_name, durable=True, arguments=retry_arguments
        )
        self._queue = await self._channel.declare_queue(self._queue_name, durable=True)

    async def publish(self, task_id: UUID, retry_count: int = 0) -> None:
        await self._publish_to(self._queue_name, task_id, retry_count)

    async def publish_retry(self, task_id: UUID, retry_count: int, delay_ms: int) -> None:
        message = self._build_message(task_id, retry_count)
        message.expiration = str(delay_ms)
        await self._publish_message(message, self._retry_queue_name)

    async def _publish_to(self, routing_key: str, task_id: UUID, retry_count: int) -> None:
        await self._publish_message(self._build_message(task_id, retry_count), routing_key)

    async def _publish_message(self, message: aio_pika.Message, routing_key: str) -> None:
        if self._channel is None or self._channel.is_closed:
            raise MessagePublishError("RabbitMQ channel is not connected")
        await self._channel.default_exchange.publish(message, routing_key=routing_key)

    @staticmethod
    def _build_message(task_id: UUID, retry_count: int) -> aio_pika.Message:
        body = json.dumps({"task_id": str(task_id), "retry_count": retry_count}).encode()
        return aio_pika.Message(
            body=body,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers={"x-retry-count": retry_count},
        )

    def iterate(self) -> AsyncIterator[AbstractIncomingMessage]:
        return self._queue.iterator()

    async def ack(self, message: AbstractIncomingMessage) -> None:
        await message.ack()

    async def close(self) -> None:
        if self._channel is not None:
            await self._channel.close()
        if self._connection is not None:
            await self._connection.close()
        self._channel = None
        self._connection = None


class UnavailableMessagePublisher(MessagePublisher):
    """Fallback publisher used when RabbitMQ is unavailable at startup.

    The API can still boot and serve reads; task creation fails with a clear
    error until the broker becomes available again.
    """

    async def publish(self, task_id: UUID) -> None:
        raise MessagePublishError("RabbitMQ is unavailable")
