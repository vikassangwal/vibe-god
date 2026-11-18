"""
Kafka Client with Resilience Patterns
"""
import asyncio
import json
import logging
from typing import Any, Dict, Optional, Callable, Awaitable, List
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError

from .base import Message, MessageBroker, MessageHandler, MessagePriority, MiddlewareChain

logger = logging.getLogger(__name__)


@dataclass
class KafkaConfig:
    """Kafka connection configuration."""
    bootstrap_servers: str = "localhost:9092"
    client_id: str = "vibe-god"
    group_id: str = "vibe-god-group"

    # Producer config
    acks: str = "all"
    retries: int = 3
    retry_backoff_ms: int = 1000
    max_batch_size: int = 16384
    linger_ms: int = 5
    compression_type: str = "snappy"
    max_in_flight_requests_per_connection: int = 5

    # Consumer config
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = True
    auto_commit_interval_ms: int = 5000
    max_poll_records: int = 500
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 10000

    # Security
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: Optional[str] = None
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None
    ssl_cafile: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None

    # Topics
    default_topic: str = "vibe-god"
    topic_partitions: int = 3
    topic_replication_factor: int = 1


@dataclass
class KafkaMessage:
    """Kafka message wrapper."""
    topic: str
    partition: int
    offset: int
    key: Optional[bytes]
    value: bytes
    timestamp: datetime
    headers: List[tuple]

    def to_message(self) -> Message:
        """Convert to base Message."""
        import json
        data = json.loads(self.value.decode())
        message = Message.from_json(json.dumps(data))
        return message


class KafkaClient(MessageBroker):
    """
    Kafka client with producer and consumer support.
    """

    def __init__(self, config: KafkaConfig):
        self.config = config
        self._producer: Optional[AIOKafkaProducer] = None
        self._consumers: Dict[str, AIOKafkaConsumer] = {}
        self._consumer_tasks: Dict[str, asyncio.Task] = {}
        self._handlers: Dict[str, MessageHandler] = {}
        self._middleware = MiddlewareChain()
        self._running = False

    async def connect(self) -> None:
        """Initialize Kafka producer."""
        if self._producer is not None:
            return

        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.config.bootstrap_servers,
            client_id=self.config.client_id,
            acks=self.config.acks,
            retries=self.config.retries,
            retry_backoff_ms=self.config.retry_backoff_ms,
            max_batch_size=self.config.max_batch_size,
            linger_ms=self.config.linger_ms,
            compression_type=self.config.compression_type,
            max_in_flight_requests_per_connection=self.config.max_in_flight_requests_per_connection,
            security_protocol=self.config.security_protocol,
            sasl_mechanism=self.config.sasl_mechanism,
            sasl_plain_username=self.config.sasl_username,
            sasl_plain_password=self.config.sasl_password,
            ssl_cafile=self.config.ssl_cafile,
            ssl_certfile=self.config.ssl_certfile,
            ssl_keyfile=self.config.ssl_keyfile,
            value_serializer=lambda v: v.to_json().encode() if isinstance(v, Message) else json.dumps(v, default=str).encode(),
            key_serializer=lambda k: k.encode() if k else None,
        )

        await self._producer.start()
        self._running = True
        logger.info(f"Connected to Kafka at {self.config.bootstrap_servers}")

    async def disconnect(self) -> None:
        """Close Kafka connections."""
        self._running = False

        # Stop all consumers
        for topic, task in self._consumer_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        for consumer in self._consumers.values():
            await consumer.stop()

        self._consumers.clear()
        self._consumer_tasks.clear()

        # Stop producer
        if self._producer:
            await self._producer.stop()
            self._producer = None

        logger.info("Disconnected from Kafka")

    async def publish(self, message: Message) -> None:
        """Publish a message to Kafka."""
        if not self._running:
            await self.connect()

        # Run middleware
        message = await self._middleware.run_before_publish(message)

        # Determine topic
        topic = message.headers.get("kafka_topic", message.topic)

        # Prepare headers
        headers = [
            (k, v.encode() if isinstance(v, str) else v)
            for k, v in message.headers.items()
        ]
        headers.extend([
            ("message_id", message.message_id.encode()),
            ("correlation_id", (message.correlation_id or "").encode()),
            ("reply_to", (message.reply_to or "").encode()),
            ("content_type", message.content_type.encode()),
            ("priority", str(message.priority.value).encode()),
        ])

        try:
            await self._producer.send_and_wait(
                topic,
                value=message,
                key=message.correlation_id.encode() if message.correlation_id else None,
                headers=headers,
                timestamp_ms=int(message.timestamp.timestamp() * 1000),
            )
            await self._middleware.run_after_publish(message, None)
            logger.debug(f"Published message {message.message_id} to {topic}")
        except Exception as e:
            logger.error(f"Failed to publish to Kafka: {e}")
            raise

    async def publish_batch(self, messages: List[Message]) -> None:
        """Publish multiple messages."""
        if not self._running:
            await self.connect()

        # Use send for batch (non-blocking)
        futures = []
        for message in messages:
            message = await self._middleware.run_before_publish(message)
            topic = message.headers.get("kafka_topic", message.topic)
            headers = [(k, v.encode() if isinstance(v, str) else v) for k, v in message.headers.items()]
            headers.extend([
                ("message_id", message.message_id.encode()),
                ("correlation_id", (message.correlation_id or "").encode()),
            ])

            future = self._producer.send(
                topic,
                value=message,
                key=message.correlation_id.encode() if message.correlation_id else None,
                headers=headers,
            )
            futures.append(future)

        # Wait for all
        for future in futures:
            try:
                await future
            except Exception as e:
                logger.error(f"Batch publish failed: {e}")
                raise

    async def subscribe(
        self,
        topic: str,
        handler: Callable[[Message], Awaitable[Any]],
        filter: Optional[Callable[[Message], bool]] = None,
        group_id: Optional[str] = None,
        partitions: Optional[List[int]] = None,
        **kwargs
    ) -> str:
        """Subscribe to a Kafka topic."""
        if not self._running:
            await self.connect()

        consumer_group = group_id or self.config.group_id

        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=self.config.bootstrap_servers,
            group_id=consumer_group,
            auto_offset_reset=self.config.auto_offset_reset,
            enable_auto_commit=self.config.enable_auto_commit,
            auto_commit_interval_ms=self.config.auto_commit_interval_ms,
            max_poll_records=self.config.max_poll_records,
            session_timeout_ms=self.config.session_timeout_ms,
            heartbeat_interval_ms=self.config.heartbeat_interval_ms,
            security_protocol=self.config.security_protocol,
            sasl_mechanism=self.config.sasl_mechanism,
            sasl_plain_username=self.config.sasl_username,
            sasl_plain_password=self.config.sasl_password,
            ssl_cafile=self.config.ssl_cafile,
            ssl_certfile=self.config.ssl_certfile,
            ssl_keyfile=self.config.ssl_keyfile,
            value_deserializer=lambda v: json.loads(v.decode()),
            key_deserializer=lambda k: k.decode() if k else None,
        )

        await consumer.start()
        self._consumers[topic] = consumer

        # Create consumer task
        task = asyncio.create_task(self._consume_loop(topic, consumer, handler, filter))
        self._consumer_tasks[topic] = task

        # Store handler
        handler_id = f"{topic}:{consumer_group}"
        self._handlers[handler_id] = MessageHandler(
            topic=topic,
            handler=handler,
            filter=filter,
        )

        logger.info(f"Subscribed to Kafka topic {topic} with group {consumer_group}")
        return handler_id

    async def _consume_loop(
        self,
        topic: str,
        consumer: AIOKafkaConsumer,
        handler: Callable[[Message], Awaitable[Any]],
        filter: Optional[Callable[[Message], bool]],
    ) -> None:
        """Main consumer loop."""
        try:
            async for msg in consumer:
                if not self._running:
                    break

                try:
                    # Parse message
                    data = msg.value
                    if isinstance(data, dict):
                        message = Message(
                            topic=data.get("topic", topic),
                            payload=data.get("payload"),
                            message_id=data.get("message_id", str(uuid.uuid4())),
                            correlation_id=data.get("correlation_id"),
                            reply_to=data.get("reply_to"),
                            headers=data.get("headers", {}),
                            priority=MessagePriority(data.get("priority", 5)),
                            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
                            ttl=data.get("ttl"),
                            content_type=data.get("content_type", "application/json"),
                        )
                    else:
                        continue

                    # Run middleware
                    message = await self._middleware.run_before_consume(message)

                    # Apply filter
                    if filter and not filter(message):
                        continue

                    # Execute handler
                    result = await handler(message)

                    # Run after-consume middleware
                    await self._middleware.run_after_consume(message, result)

                except Exception as e:
                    logger.error(f"Error processing Kafka message: {e}")
                    await self._middleware.run_on_error(message, e)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Consumer loop error: {e}")

    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from topic."""
        if subscription_id in self._handlers:
            handler = self._handlers.pop(subscription_id)
            topic = handler.topic

            # Stop consumer task
            if topic in self._consumer_tasks:
                task = self._consumer_tasks.pop(topic)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Stop consumer
            if topic in self._consumers:
                await self._consumers[topic].stop()
                del self._consumers[topic]

            logger.info(f"Unsubscribed from Kafka topic {topic}")

    async def health_check(self) -> bool:
        """Check Kafka connection health."""
        try:
            if not self._running or not self._producer:
                return False
            # Check if producer can send
            metadata = await self._producer.client.fetch_cluster_metadata()
            return len(metadata.brokers()) > 0
        except Exception:
            return False

    def add_middleware(self, middleware) -> None:
        """Add middleware to chain."""
        self._middleware.add(middleware)

    @property
    def is_running(self) -> bool:
        return self._running

    async def create_topic(
        self,
        topic: str,
        partitions: Optional[int] = None,
        replication_factor: Optional[int] = None,
    ) -> None:
        """Create a Kafka topic (requires admin rights)."""
        from aiokafka.admin import AIOKafkaAdminClient, NewTopic

        admin = AIOKafkaAdminClient(
            bootstrap_servers=self.config.bootstrap_servers,
            client_id=f"{self.config.client_id}-admin",
        )

        await admin.start()
        try:
            new_topic = NewTopic(
                name=topic,
                num_partitions=partitions or self.config.topic_partitions,
                replication_factor=replication_factor or self.config.topic_replication_factor,
            )
            await admin.create_topics([new_topic])
            logger.info(f"Created topic {topic}")
        except Exception as e:
            logger.warning(f"Topic creation failed (may already exist): {e}")
        finally:
            await admin.close()

    async def list_topics(self) -> List[str]:
        """List available topics."""
        try:
            metadata = await self._producer.client.fetch_cluster_metadata()
            return list(metadata.topics())
        except Exception:
            return []