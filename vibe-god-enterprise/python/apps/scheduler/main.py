"""
Vibe-God Enterprise Scheduler Service
Scheduled task execution with APScheduler
"""
import os
import asyncio
import signal
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from python.libs.observability import (
    configure_logging,
    init_tracing,
    init_metrics,
    get_logger,
)
from python.libs.database import init_database, close_database, get_database
from python.libs.security import get_secrets_manager
from python.libs.messaging import KafkaClient, KafkaConfig
from python.libs.database.models import Task
from python.libs.database.repository import TaskRepository
from python.libs.database.session import transaction_scope

# Configure logging
configure_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    json_output=os.getenv("LOG_FORMAT", "json") == "json",
    service_name="vibe-god-scheduler",
    otlp_endpoint=os.getenv("OTLP_ENDPOINT"),
)

init_tracing(
    service_name="vibe-god-scheduler",
    otlp_endpoint=os.getenv("OTLP_ENDPOINT"),
    service_version=os.getenv("APP_VERSION", "1.0.0"),
)

init_metrics(
    service_name="vibe-god-scheduler",
    otlp_endpoint=os.getenv("OTLP_ENDPOINT"),
)

logger = get_logger(__name__)

# Global state
running = True
kafka_client: Optional[KafkaClient] = None
scheduler: Optional[AsyncIOScheduler] = None


class TaskScheduler:
    """Scheduled task executor."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(
            jobstores={
                "default": SQLAlchemyJobStore(
                    url=os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/vibe_god")
                )
            },
            executors={
                "default": ThreadPoolExecutor(20),
            },
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 300,
            },
            timezone="UTC",
        )

    async def start(self):
        """Start the scheduler."""
        global kafka_client

        logger.info("Starting scheduler")

        # Initialize database
        await init_database()

        # Connect to Kafka
        await self._connect_kafka()

        # Load scheduled jobs from database
        await self._load_scheduled_jobs()

        # Add built-in jobs
        self._add_builtin_jobs()

        # Start scheduler
        self.scheduler.start()

        logger.info("Scheduler started successfully")

    async def stop(self):
        """Stop the scheduler."""
        global running
        running = False
        logger.info("Stopping scheduler")

        if self.scheduler:
            self.scheduler.shutdown(wait=True)

        if kafka_client:
            await kafka_client.disconnect()

        await close_database()
        logger.info("Scheduler stopped")

    async def _connect_kafka(self):
        """Connect to Kafka."""
        global kafka_client

        secrets_manager = get_secrets_manager()

        kafka_config = KafkaConfig(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            client_id="vibe-god-scheduler",
            group_id="vibe-god-scheduler",
        )
        kafka_client = KafkaClient(kafka_config)
        await kafka_client.connect()

    async def _load_scheduled_jobs(self):
        """Load scheduled jobs from database."""
        async with transaction_scope() as session:
            repo = TaskRepository(Task, session)

            # Get all scheduled tasks
            tasks = await repo.get_all(
                Task.status == "scheduled",
                Task.scheduled_at is not None,
            )

            for task in tasks:
                self._schedule_task(task)

    def _add_builtin_jobs(self):
        """Add built-in maintenance jobs."""
        # Cleanup old completed tasks daily at 2 AM
        self.scheduler.add_job(
            self._cleanup_old_tasks,
            CronTrigger(hour=2, minute=0),
            id="cleanup_old_tasks",
            name="Cleanup old completed tasks",
            replace_existing=True,
        )

        # Retry failed tasks every 15 minutes
        self.scheduler.add_job(
            self._retry_failed_tasks,
            IntervalTrigger(minutes=15),
            id="retry_failed_tasks",
            name="Retry failed tasks",
            replace_existing=True,
        )

        # Health check every minute
        self.scheduler.add_job(
            self._health_check,
            IntervalTrigger(minutes=1),
            id="health_check",
            name="Scheduler health check",
            replace_existing=True,
        )

        # Publish scheduler metrics every 30 seconds
        self.scheduler.add_job(
            self._publish_metrics,
            IntervalTrigger(seconds=30),
            id="publish_metrics",
            name="Publish scheduler metrics",
            replace_existing=True,
        )

    def _schedule_task(self, task: Task):
        """Schedule a task based on its configuration."""
        job_id = f"task-{task.id}"

        # Remove existing job if any
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

        # Determine trigger
        if task.payload.get("cron"):
            trigger = CronTrigger.from_crontab(task.payload["cron"])
        elif task.payload.get("interval_seconds"):
            trigger = IntervalTrigger(seconds=task.payload["interval_seconds"])
        elif task.scheduled_at:
            trigger = DateTrigger(run_date=task.scheduled_at)
        else:
            logger.warning("Task has no valid trigger", task_id=task.id)
            return

        # Schedule the job
        self.scheduler.add_job(
            self._execute_task,
            trigger,
            args=[task.id],
            id=job_id,
            name=f"Task: {task.name}",
            replace_existing=True,
            max_instances=1,
        )

        logger.info("Scheduled task", task_id=task.id, job_id=job_id)

    async def _execute_task(self, task_id: str):
        """Execute a scheduled task."""
        logger.info("Executing scheduled task", task_id=task_id)

        async with transaction_scope() as session:
            repo = TaskRepository(Task, session)
            task = await repo.get_by_id(task_id)

            if not task:
                logger.warning("Task not found", task_id=task_id)
                return

            if task.status != "scheduled":
                logger.warning("Task not in scheduled state", task_id=task_id, status=task.status)
                return

            # Update task status
            task.status = "running"
            task.started_at = datetime.utcnow()
            await session.flush()

        try:
            # Publish task to Kafka for worker to pick up
            if kafka_client:
                from python.libs.messaging.base import Message, MessagePriority
                task_msg = Message(
                    topic=task.payload.get("queue", "default"),
                    payload={
                        "task_id": str(task.id),
                        "task_name": task.name,
                        "task_type": task.payload.get("task_type"),
                        "payload": task.payload,
                    },
                    priority=MessagePriority.NORMAL,
                )
                await kafka_client.publish(task_msg)

            # Update task status to queued
            async with transaction_scope() as session:
                repo = TaskRepository(Task, session)
                task = await repo.get_by_id(task_id)
                if task:
                    task.status = "queued"
                    await session.flush()

            logger.info("Task queued for execution", task_id=task_id)

        except Exception as e:
            logger.error("Failed to queue task", task_id=task_id, error=str(e))

            # Mark task as failed
            async with transaction_scope() as session:
                repo = TaskRepository(Task, session)
                task = await repo.get_by_id(task_id)
                if task:
                    task.status = "failed"
                    task.error = str(e)
                    task.completed_at = datetime.utcnow()
                    await session.flush()

    async def _cleanup_old_tasks(self):
        """Clean up old completed/failed tasks."""
        logger.info("Running cleanup job")

        async with transaction_scope() as session:
            repo = TaskRepository(Task, session)

            # Delete tasks older than 30 days
            cutoff = datetime.utcnow() - timedelta(days=30)

            # This would need a custom delete query
            # For now, just log
            logger.info("Cleanup job completed")

    async def _retry_failed_tasks(self):
        """Retry failed tasks that haven't exceeded max retries."""
        logger.info("Running retry job")

        async with transaction_scope() as session:
            repo = TaskRepository(Task, session)

            # Get failed tasks that can be retried
            tasks = await repo.get_all(
                Task.status == "failed",
                Task.retry_count < Task.max_retries,
            )

            for task in tasks:
                task.status = "scheduled"
                task.scheduled_at = datetime.utcnow() + timedelta(minutes=5)
                task.error = None
                await session.flush()

                # Reschedule
                self._schedule_task(task)

            if tasks:
                logger.info("Scheduled failed tasks for retry", count=len(tasks))

    async def _health_check(self):
        """Periodic health check."""
        try:
            # Check database
            db = await get_database()
            db_healthy = await db.health_check()

            # Check Kafka
            kafka_healthy = kafka_client.is_running if kafka_client else False

            if not db_healthy or not kafka_healthy:
                logger.warning("Health check failed", database=db_healthy, kafka=kafka_healthy)

        except Exception as e:
            logger.error("Health check error", error=str(e))

    async def _publish_metrics(self):
        """Publish scheduler metrics."""
        if not kafka_client:
            return

        try:
            from python.libs.messaging.base import Message, MessagePriority

            # Get job count
            jobs = self.scheduler.get_jobs()

            metrics_msg = Message(
                topic="scheduler.metrics",
                payload={
                    "timestamp": datetime.utcnow().isoformat(),
                    "total_jobs": len(jobs),
                    "running_jobs": len([j for j in jobs if j.next_run_time]),
                    "job_details": [
                        {
                            "id": job.id,
                            "name": job.name,
                            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                        }
                        for job in jobs
                    ],
                },
                priority=MessagePriority.LOW,
            )

            await kafka_client.publish(metrics_msg)

        except Exception as e:
            logger.error("Failed to publish metrics", error=str(e))


async def main():
    """Main entry point."""
    global running, scheduler

    scheduler = TaskScheduler()

    # Handle shutdown signals
    def signal_handler(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        await scheduler.start()

        # Wait until stopped
        while running:
            await asyncio.sleep(1)

    finally:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())