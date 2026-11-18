"""
RabbitMQ Client with Resilience Patterns
"""
import asyncio
import json
import logging
from typing import Any, Dict, Optional, Callable, Awaitable, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

import aio_pika
from aio_pika import ExchangeType, Message as AioPikaMessage, DeliveryMode
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractQueue, AbstractExchange

from .base import Message, MessageBroker, MessageHandler, MessagePriority, MiddlewareChain, DeadLetterMessage

logger = logging.getLogger(__name__)


class ExchangeType(str, Enum):
    DIRECT = "direct"
    TOPIC = "topic"
    FANOUT = "fanout"
    HEADERS = "headers"


@dataclass
class RabbitMQConfig:
    """RabbitMQ connection configuration."""
    host: str = "localhost"
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    virtual_host: str = "/"
    connection_timeout: float = 10.0
    heartbeat: int = 60
    prefetch_count: int = 10
    publisher_confirms: bool = True
    ssl: bool = False
    ssl_options: Optional[Dict] = None

    # Retry configuration
    max_reconnect_attempts: int = 10
    reconnect_delay: float = 5.0
    reconnect_max_delay: float = 60.0

    @property
    def url(self) -> str:
        protocol = "amqps" if self.ssl else "amqp"
        return f"{protocol}://{self.username}:{self.password}@{self.host}:{self.port}{self.virtual_host}"


class RabbitMQClient(MessageBroker):
    """
    RabbitMQ client with automatic reconnection, publisher confirms,
    and resilience patterns.
    """

    def __init__(self, config: RabbitMQConfig):
        self.config = config
        self._connection: Optional[AbstractConnection] = None
        self._channel: Optional[AbstractChannel] = None
        self._exchanges: Dict[str, AbstractExchange] = {}
        self._queues: Dict[str, AbstractQueue] = {}
        self._consumers: Dict[str, asyncio.Task] = {}
        self._handlers: Dict[str, MessageHandler] = {}
        self._middleware = MiddlewareChain()
        self._reconnect_task: Optional[asyncio.Task] = None
        self._connected = False
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        async with self._lock:
            if self._connected:
                return

            try:
                self._connection = await aio_pika.connect_robust(
                    self.config.url,
                    timeout=self.config.connection_timeout,
                    heartbeat=self.config.heartbeat,
                )

                self._channel = await self._connection.channel()
                await self._channel.set_qos(prefetch_count=self.config.prefetch_count)

                if self.config.publisher_confirms:
                    await self._channel.enable_publisher_confirms()

                # Set up connection callbacks
                self._connection.close_callbacks.add(self._on_connection_closed)

                self._connected = True
                logger.info("Connected to RabbitMQ")

                # Re-declare exchanges and queues
                await self._redeclare_topology()

            except Exception as e:
                logger.error(f"Failed to connect to RabbitMQ: {e}")
                self._connected = False
                raise

    async def disconnect(self) -> None:
        """Close connection to RabbitMQ."""
        async with self._lock:
            self._connected = False

            # Cancel reconnect task
            if self._reconnect_task:
                self._reconnect_task.cancel()
                try:
                    await self._reconnect_task
                except asyncio.CancelledError:
                    pass

            # Stop all consumers
            for consumer_tag, task in self._consumers.items():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            self._consumers.clear()

            # Close channel and connection
            if self._channel and not self._channel.is_closed:
                await self._channel.close()

            if self._connection and not self._connection.is_closed:
                await self._connection.close()

            self._exchanges.clear()
            self._queues.clear()
            logger.info("Disconnected from RabbitMQ")

    async def _on_connection_closed(self, connection: AbstractConnection, reason: Exception) -> None:
        """Handle connection closure."""
        logger.warning(f"RabbitMQ connection closed: {reason}")
        self._connected = False

        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        delay = self.config.reconnect_delay
        attempt = 0

        while attempt < self.config.max_reconnect_attempts:
            try:
                await asyncio.sleep(delay)
                await self.connect()
                logger.info("Reconnected to RabbitMQ")
                return
            except Exception as e:
                attempt += 1
                logger.warning(f"Reconnection attempt {attempt} failed: {e}")
                delay = min(delay * 2, self.config.reconnect_max_delay)

        logger.error("Max reconnection attempts reached")

    async def _redeclare_topology(self) -> None:
        """Re-declare exchanges and queues after reconnection."""
        # Re-declare exchanges
        for name, exchange in self._exchanges.items():
            if exchange.is_closed:
                new_exchange = await self._channel.declare_exchange(
                    name,
                    type=exchange.type,
                    durable=True,
                )
                self._exchanges[name] = new_exchange

        # Re-declare queues and bind
        for name, queue in self._queues.items():
            if queue.is_closed:
                new_queue = await self._channel.declare_queue(name, durable=True)
                self._queues[name] = new_queue

                # Re-bind to exchanges (would need binding info stored)

    async def declare_exchange(
        self,
        name: str,
        type: ExchangeType = ExchangeType.TOPIC,
        durable: bool = True,
        **kwargs
    ) -> AbstractExchange:
        """Declare an exchange."""
        if not self._connected:
            await self.connect()

        exchange = await self._channel.declare_exchange(
            name,
            type=type.value,
            durable=durable,
            **kwargs
        )
        self._exchanges[name] = exchange
        return exchange

    async def declare_queue(
        self,
        name: str,
        durable: bool = True,
        arguments: Optional[Dict] = None,
        **kwargs
    ) -> AbstractQueue:
        """Declare a queue."""
        if not self._connected:
            await self.connect()

        queue = await self._channel.declare_queue(
            name,
            durable=durable,
            arguments=arguments,
            **kwargs
        )
        self._queues[name] = queue
        return queue

    async def bind_queue(
        self,
        queue_name: str,
        exchange_name: str,
        routing_key: str,
        **kwargs
    ) -> None:
        """Bind queue to exchange."""
        if not self._connected:
            await self.connect()

        queue = self._queues.get(queue_name)
        exchange = self._exchanges.get(exchange_name)

        if not queue:
            queue = await self.declare_queue(queue_name)
        if not exchange:
            exchange = await self.declare_exchange(exchange_name)

        await queue.bind(exchange, routing_key, **kwargs)

    async def publish(self, message: Message) -> None:
        """Publish a message."""
        if not self._connected:
            await self.connect()

        # Run middleware
        message = await self._middleware.run_before_publish(message)

        # Get or create exchange
        exchange_name = message.headers.get("exchange", "default")
        exchange = self._exchanges.get(exchange_name)
        if not exchange:
            exchange = await self.declare_exchange(exchange_name)

        # Prepare message
        routing_key = message.headers.get("routing_key", message.topic)
        priority = message.priority.value

        aio_message = AioPikaMessage(
            body=message.to_json().encode(),
            message_id=message.message_id,
            correlation_id=message.correlation_id,
            reply_to=message.reply_to,
            headers=message.headers,
            priority=priority,
            expiration=str(message.ttl * 1000) if message.ttl else None,
            content_type=message.content_type,
            delivery_mode=DeliveryMode.PERSISTENT,
            timestamp=message.timestamp,
        )

        # Publish with confirmation
        try:
            await exchange.publish(
                aio_message,
                routing_key=routing_key,
                mandatory=True,
            )
            await self._middleware.run_after_publish(message, None)
            logger.debug(f"Published message {message.message_id} to {exchange_name}/{routing_key}")
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            raise

    async def publish_batch(self, messages: List[Message]) -> None:
        """Publish multiple messages."""
        # Use publisher confirms for batch
        if not self._connected:
            await self.connect()

        for message in messages:
            await self.publish(message)

    async def subscribe(
        self,
        topic: str,
        handler: Callable[[Message], Awaitable[Any]],
        filter: Optional[Callable[[Message], bool]] = None,
        queue_name: Optional[str] = None,
        exchange_name: str = "default",
        routing_key: Optional[str] = None,
        durable: bool = True,
        arguments: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """Subscribe to a topic."""
        if not self._connected:
            await self.connect()

        # Generate queue name if not provided
        if queue_name is None:
            queue_name = f"vibe-god.{topic}.{uuid.uuid4().hex[:8]}"

        # Declare queue
        queue = await self.declare_queue(queue_name, durable=durable, arguments=arguments)

        # Bind to exchange
        if routing_key is None:
            routing_key = topic
        await self.bind_queue(queue_name, exchange_name, routing_key)

        # Create handler wrapper
        async def message_handler(aio_message: aio_pika.abc.AbstractIncomingMessage):
            async with aio_message.process():
                try:
                    # Parse message
                    body = aio_message.body.decode()
                    message = Message.from_json(body)

                    # Run before-consume middleware
                    message = await self._middleware.run_before_consume(message)

                    # Apply filter
                    if filter and not filter(message):
                        return

                    # Execute handler
                    result = await handler(message)

                    # Run after-consume middleware
                    await self._middleware.run_after_consume(message, result)

                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self._middleware.run_on_error(message, e)
                    raise

        # Start consuming
        consumer_tag = await queue.consume(message_handler)
        self._consumers[consumer_tag] = asyncio.current_task()

        # Store handler
        handler_id = f"{queue_name}:{consumer_tag}"
        self._handlers[handler_id] = MessageHandler(
            topic=topic,
            handler=handler,
            filter=filter,
        )

        logger.info(f"Subscribed to {topic} with queue {queue_name}")
        return handler_id

    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from topic."""
        if subscription_id in self._handlers:
            handler = self._handlers.pop(subscription_id)
            # Find and cancel consumer
            for consumer_tag, task in list(self._consumers.items()):
                if consumer_tag in subscription_id:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    del self._consumers[consumer_tag]
                    break
            logger.info(f"Unsubscribed {subscription_id}")

    async def health_check(self) -> bool:
        """Check RabbitMQ connection health."""
        try:
            if not self._connected or not self._connection:
                return False
            if self._connection.is_closed:
                return False
            # Try a simple operation
            await self._channel.declare_queue("health-check", passive=True)
            return True
        except Exception:
            return False

    def add_middleware(self, middleware) -> None:
        """Add middleware to chain."""
        self._middleware.add(middleware)

    @property
    def is_connected(self) -> bool:
        return self._connected and self._connection and not self._connection.is_closed

    async def get_queue_info(self, queue_name: str) -> Dict[str, Any]:
        """Get queue information."""
        if queue_name in self._queues:
            queue = self._queues[queue_name]
            return {
                "name": queue.name,
                "message_count": queue.declaration_result.message_count if queue.declaration_result else 0,
                "consumer_count": queue.declaration_result.consumer_count if queue.declaration_result else 0,
            }
        return {}