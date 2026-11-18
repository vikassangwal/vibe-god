"""
Base Messaging Interfaces and Types
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable, Awaitable, List
from enum import Enum
import json
import uuid
from datetime import datetime


class MessagePriority(int, Enum):
    LOW = 0
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class Message:
    """Base message structure."""
    topic: str
    payload: Any
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ttl: Optional[int] = None  # Time to live in seconds
    content_type: str = "application/json"

    def to_json(self) -> str:
        """Serialize to JSON."""
        data = {
            "message_id": self.message_id,
            "topic": self.topic,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "headers": self.headers,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "ttl": self.ttl,
            "content_type": self.content_type,
        }
        return json.dumps(data, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        """Deserialize from JSON."""
        data = json.loads(json_str)
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["priority"] = MessagePriority(data["priority"])
        return cls(**data)


@dataclass
class MessageHandler:
    """Message handler registration."""
    topic: str
    handler: Callable[[Message], Awaitable[Any]]
    filter: Optional[Callable[[Message], bool]] = None
    concurrent: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0


class MessageBroker(ABC):
    """Abstract message broker interface."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to broker."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from broker."""
        pass

    @abstractmethod
    async def publish(self, message: Message) -> None:
        """Publish a message."""
        pass

    @abstractmethod
    async def subscribe(
        self,
        topic: str,
        handler: Callable[[Message], Awaitable[Any]],
        filter: Optional[Callable[[Message], bool]] = None,
        **kwargs
    ) -> str:
        """Subscribe to topic."""
        pass

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from topic."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check broker health."""
        pass


class Publisher(ABC):
    """Message publisher interface."""

    @abstractmethod
    async def publish(self, message: Message) -> None:
        """Publish a message."""
        pass

    @abstractmethod
    async def publish_batch(self, messages: List[Message]) -> None:
        """Publish multiple messages."""
        pass


class Consumer(ABC):
    """Message consumer interface."""

    @abstractmethod
    async def start(self) -> None:
        """Start consuming."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop consuming."""
        pass

    @abstractmethod
    def add_handler(
        self,
        topic: str,
        handler: Callable[[Message], Awaitable[Any]],
        filter: Optional[Callable[[Message], bool]] = None,
        **kwargs
    ) -> str:
        """Add message handler."""
        pass

    @abstractmethod
    def remove_handler(self, handler_id: str) -> None:
        """Remove message handler."""
        pass


# Dead Letter Queue message
@dataclass
class DeadLetterMessage:
    """Message that failed processing."""
    original_message: Message
    error: str
    retry_count: int
    failed_at: datetime = field(default_factory=datetime.utcnow)
    handler_name: str = ""


# Message middleware for cross-cutting concerns
class MessageMiddleware:
    """Middleware for message processing."""

    async def before_publish(self, message: Message) -> Message:
        """Called before publishing."""
        return message

    async def after_publish(self, message: Message, result: Any) -> Any:
        """Called after publishing."""
        return result

    async def before_consume(self, message: Message) -> Message:
        """Called before consuming."""
        return message

    async def after_consume(self, message: Message, result: Any) -> Any:
        """Called after consuming."""
        return result

    async def on_error(self, message: Message, error: Exception) -> None:
        """Called on processing error."""
        pass


# Middleware chain
class MiddlewareChain:
    """Chain of middleware."""

    def __init__(self):
        self._middlewares: List[MessageMiddleware] = []

    def add(self, middleware: MessageMiddleware) -> None:
        """Add middleware to chain."""
        self._middlewares.append(middleware)

    async def run_before_publish(self, message: Message) -> Message:
        """Run before-publish middleware."""
        for mw in self._middlewares:
            message = await mw.before_publish(message)
        return message

    async def run_after_publish(self, message: Message, result: Any) -> Any:
        """Run after-publish middleware."""
        for mw in reversed(self._middlewares):
            result = await mw.after_publish(message, result)
        return result

    async def run_before_consume(self, message: Message) -> Message:
        """Run before-consume middleware."""
        for mw in self._middlewares:
            message = await mw.before_consume(message)
        return message

    async def run_after_consume(self, message: Message, result: Any) -> Any:
        """Run after-consume middleware."""
        for mw in reversed(self._middlewares):
            result = await mw.after_consume(message, result)
        return result

    async def run_on_error(self, message: Message, error: Exception) -> None:
        """Run error middleware."""
        for mw in self._middlewares:
            await mw.on_error(message, error)


# Serialization helpers
def serialize_message(message: Message, format: str = "json") -> bytes:
    """Serialize message to bytes."""
    if format == "json":
        return message.to_json().encode()
    elif format == "msgpack":
        try:
            import msgpack
            return msgpack.packb({
                "message_id": message.message_id,
                "topic": message.topic,
                "payload": message.payload,
                "correlation_id": message.correlation_id,
                "reply_to": message.reply_to,
                "headers": message.headers,
                "priority": message.priority.value,
                "timestamp": message.timestamp.isoformat(),
                "ttl": message.ttl,
                "content_type": message.content_type,
            })
        except ImportError:
            raise ValueError("msgpack not installed")
    else:
        raise ValueError(f"Unknown format: {format}")


def deserialize_message(data: bytes, format: str = "json") -> Message:
    """Deserialize message from bytes."""
    if format == "json":
        return Message.from_json(data.decode())
    elif format == "msgpack":
        try:
            import msgpack
            unpacked = msgpack.unpackb(data)
            unpacked["timestamp"] = datetime.fromisoformat(unpacked["timestamp"])
            unpacked["priority"] = MessagePriority(unpacked["priority"])
            return Message(**unpacked)
        except ImportError:
            raise ValueError("msgpack not installed")
    else:
        raise ValueError(f"Unknown format: {format}")