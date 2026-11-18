"""
Enterprise Messaging Library for Vibe-God
Provides RabbitMQ and Kafka clients with resilience patterns.
"""

from .rabbitmq import RabbitMQClient, RabbitMQConfig, Message, ExchangeType
from .kafka import KafkaClient, KafkaConfig, KafkaMessage
from .base import MessageBroker, MessageHandler

__all__ = [
    "RabbitMQClient",
    "RabbitMQConfig",
    "Message",
    "ExchangeType",
    "KafkaClient",
    "KafkaConfig",
    "KafkaMessage",
    "MessageBroker",
    "MessageHandler",
]