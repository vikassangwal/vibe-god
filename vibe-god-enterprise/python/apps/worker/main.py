"""
Vibe-God Enterprise Worker Service
Background task processing with Celery-like functionality
"""
import os
import asyncio
import signal
from contextlib import asynccontextmanager
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

import structlog
from python.libs.observability import (
    configure_logging,
    init_tracing,
    init_metrics,
    get_logger,
)
from python.libs.database import init_database, close_database, get_database
from python.libs.security import get_secrets_manager
from python.libs.messaging import RabbitMQClient, RabbitMQConfig, KafkaClient, KafkaConfig
from python.libs.resilience import get_circuit_breaker, CircuitBreakerConfig
from python.libs.database.models import Task
from python.libs.database.repository import TaskRepository
from python.libs.database.session import transaction_scope

# Configure logging
configure_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    json_output=os.getenv("LOG_FORMAT", "json") == "json",
    service_name="vibe-god-worker",
    otlp_endpoint=os.getenv("OTLP_ENDPOINT"),
)

init_tracing(
    service_name="vibe-god-worker",
    otlp_endpoint=os.getenv("OTLP_ENDPOINT"),
    service_version=os.getenv("APP_VERSION", "1.0.0"),
)

init_metrics(
    service_name="vibe-god-worker",
    otlp_endpoint=os.getenv("OTLP_ENDPOINT"),
)

logger = get_logger(__name__)

# Global state
running = True
rabbitmq_client: Optional[RabbitMQClient] = None
kafka_client: Optional[KafkaClient] = None
worker_id = f"worker-{os.getpid()}-{datetime.utcnow().timestamp()}"


@dataclass
class WorkerConfig:
    concurrency: int = 4
    prefetch_count: int = 10
    queues: List[str] = None

    def __post_init__(self):
        if self.queues is None:
            self.queues = ["default", "emitra", "twitter", "documents", "reports"]


class TaskWorker:
    """Background task worker."""

    def __init__(self, config: WorkerConfig):
        self.config = config
        self.semaphore = asyncio.Semaphore(config.concurrency)
        self.tasks: List[asyncio.Task] = []

    async def start(self):
        """Start the worker."""
        logger.info("Starting worker", worker_id=worker_id, concurrency=self.config.concurrency)

        # Connect to message brokers
        await self._connect_brokers()

        # Start consuming from queues
        for queue in self.config.queues:
            task = asyncio.create_task(self._consume_queue(queue))
            self.tasks.append(task)

        # Start heartbeat
        heartbeat_task = asyncio.create_task(self._heartbeat())
        self.tasks.append(heartbeat_task)

        logger.info("Worker started successfully")

    async def stop(self):
        """Stop the worker."""
        global running
        running = False
        logger.info("Stopping worker", worker_id=worker_id)

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)

        # Disconnect brokers
        if rabbitmq_client:
            await rabbitmq_client.disconnect()
        if kafka_client:
            await kafka_client.disconnect()

        logger.info("Worker stopped")

    async def _connect_brokers(self):
        """Connect to message brokers."""
        global rabbitmq_client, kafka_client

        secrets_manager = get_secrets_manager()

        # RabbitMQ
        rabbitmq_config = RabbitMQConfig(
            host=os.getenv("RABBITMQ_HOST", "localhost"),
            port=int(os.getenv("RABBITMQ_PORT", "5672")),
            username=os.getenv("RABBITMQ_USER", "guest"),
            password=await secrets_manager.get_secret_required("rabbitmq.password"),
            virtual_host=os.getenv("RABBITMQ_VHOST", "/"),
            prefetch_count=self.config.prefetch_count,
        )
        rabbitmq_client = RabbitMQClient(rabbitmq_config)
        await rabbitmq_client.connect()

        # Kafka
        kafka_config = KafkaConfig(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            client_id=f"vibe-god-worker-{worker_id}",
            group_id="vibe-god-workers",
        )
        kafka_client = KafkaClient(kafka_config)
        await kafka_client.connect()

    async def _consume_queue(self, queue_name: str):
        """Consume messages from a queue."""
        logger.info("Starting consumer", queue=queue_name)

        try:
            await rabbitmq_client.subscribe(
                topic=queue_name,
                handler=self._process_message,
                queue_name=f"vibe-god.{queue_name}",
                durable=True,
            )

            # Keep the consumer running
            while running:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Consumer cancelled", queue=queue_name)
        except Exception as e:
            logger.error("Consumer error", queue=queue_name, error=str(e))

    async def _process_message(self, message):
        """Process a message."""
        async with self.semaphore:
            logger.info("Processing message", message_id=message.message_id, topic=message.topic)

            try:
                # Route to appropriate handler based on topic
                if message.topic == "emitra":
                    await self._handle_emitra_task(message)
                elif message.topic == "twitter":
                    await self._handle_twitter_task(message)
                elif message.topic == "documents":
                    await self._handle_document_task(message)
                elif message.topic == "reports":
                    await self._handle_report_task(message)
                else:
                    await self._handle_generic_task(message)

                logger.info("Message processed successfully", message_id=message.message_id)

            except Exception as e:
                logger.error("Message processing failed", message_id=message.message_id, error=str(e))
                raise

    async def _handle_emitra_task(self, message):
        """Handle eMitra automation task."""
        from core.emitra_bot import EmitaBot
        from core.config import load_config

        config = load_config()
        bot = EmitaBot(config)

        task_type = message.payload.get("task_type")
        if task_type == "form_fill":
            await bot.fill_form(message.payload.get("service"), message.payload.get("data"))
        elif task_type == "document_upload":
            await bot.upload_document(message.payload.get("service"), message.payload.get("file_path"))
        elif task_type == "payment":
            await bot.process_payment(message.payload.get("service"), message.payload.get("amount"))

    async def _handle_twitter_task(self, message):
        """Handle Twitter automation task."""
        from bots.twitter_bot import TwitterBot
        from core.config import load_config

        config = load_config()
        bot = TwitterBot(config)

        task_type = message.payload.get("task_type")
        if task_type == "tweet":
            await bot.post_tweet(message.payload.get("text"))
        elif task_type == "reply":
            await bot.reply_to_tweet(message.payload.get("tweet_id"), message.payload.get("text"))
        elif task_type == "dm":
            await bot.send_dm(message.payload.get("user_id"), message.payload.get("text"))
        elif task_type == "scrape":
            await bot.scrape_hashtag(message.payload.get("hashtag"))

    async def _handle_document_task(self, message):
        """Handle document processing task."""
        from modules.doc_processor import DocumentProcessor

        processor = DocumentProcessor()
        task_type = message.payload.get("task_type")

        if task_type == "ocr":
            await processor.process_document(message.payload.get("file_path"))
        elif task_type == "compress":
            await processor.compress_image(
                message.payload.get("input_path"),
                message.payload.get("output_path"),
                message.payload.get("target_size_kb", 100)
            )

    async def _handle_report_task(self, message):
        """Handle report generation task."""
        from modules.data_products import DataProductsGenerator

        generator = DataProductsGenerator()
        report_type = message.payload.get("report_type")

        if report_type == "mandi_weekly":
            await generator.generate_mandi_weekly_report(message.payload.get("week"))
        elif report_type == "crop_calendar":
            await generator.generate_crop_calendar(message.payload.get("crop"))

    async def _handle_generic_task(self, message):
        """Handle generic task."""
        logger.info("Processing generic task", payload=message.payload)

    async def _heartbeat(self):
        """Send worker heartbeat."""
        while running:
            try:
                # Update worker status in database
                async with transaction_scope() as session:
                    repo = TaskRepository(Task, session)
                    # Could update worker registry here
                    pass

                # Publish heartbeat to Kafka
                if kafka_client:
                    from python.libs.messaging.base import Message, MessagePriority
                    heartbeat_msg = Message(
                        topic="worker.heartbeat",
                        payload={
                            "worker_id": worker_id,
                            "timestamp": datetime.utcnow().isoformat(),
                            "status": "healthy",
                            "concurrency": self.config.concurrency,
                            "active_tasks": self.config.concurrency - self.semaphore._value,
                        },
                        priority=MessagePriority.LOW,
                    )
                    await kafka_client.publish(heartbeat_msg)

            except Exception as e:
                logger.error("Heartbeat failed", error=str(e))

            await asyncio.sleep(30)  # Heartbeat every 30 seconds


async def main():
    """Main entry point."""
    global running

    # Load configuration
    config = WorkerConfig(
        concurrency=int(os.getenv("WORKER_CONCURRENCY", "4")),
        prefetch_count=int(os.getenv("WORKER_PREFETCH", "10")),
    )

    # Initialize database
    await init_database()

    # Create and start worker
    worker = TaskWorker(config)

    # Handle shutdown signals
    def signal_handler(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        await worker.start()

        # Wait until stopped
        while running:
            await asyncio.sleep(1)

    finally:
        await worker.stop()
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())