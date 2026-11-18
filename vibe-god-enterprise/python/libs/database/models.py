"""
Database Models - Base Classes and Mixins
"""
import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    Text,
    Index,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, declared_attr, Mapped, mapped_column
from sqlalchemy.ext.declarative import DeclarativeMeta

# Create base with naming convention
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

Base = declarative_base(metadata=metadata)


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin for soft delete support."""

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    @property
    def is_active(self) -> bool:
        return not self.is_deleted

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = func.now()

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None


class UUIDMixin:
    """Mixin for UUID primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )


class MetadataMixin:
    """Mixin for flexible JSON metadata."""

    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model with UUID and timestamps."""

    __abstract__ = True


class SoftDeleteModel(BaseModel, SoftDeleteMixin):
    """Base model with soft delete support."""

    __abstract__ = True


# Event listeners for updated_at
@event.listens_for(BaseModel, "before_update", propagate=True)
def update_timestamp(mapper, connection, target):
    """Auto-update updated_at on model update."""
    if hasattr(target, "updated_at"):
        target.updated_at = func.now()


# Common indexes
def create_common_indexes(table_name: str) -> list:
    """Create common indexes for a table."""
    return [
        Index(f"ix_{table_name}_created_at", "created_at"),
        Index(f"ix_{table_name}_updated_at", "updated_at"),
    ]


# Example models for vibe-god
class User(SoftDeleteModel):
    """User model."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    roles: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    permissions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        *create_common_indexes("users"),
        Index("ix_users_email_status", "email", "status"),
    )


class AuditLog(BaseModel):
    """Audit log model."""

    __tablename__ = "audit_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="success", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        *create_common_indexes("audit_logs"),
        Index("ix_audit_logs_user_action", "user_id", "action"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_created_at_status", "created_at", "status"),
    )


class ApiKey(BaseModel):
    """API Key model."""

    __tablename__ = "api_keys"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    scopes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        *create_common_indexes("api_keys"),
        Index("ix_api_keys_user_active", "user_id", "is_active"),
    )


class Session(BaseModel):
    """User session model."""

    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        *create_common_indexes("sessions"),
        Index("ix_sessions_user_expires", "user_id", "expires_at"),
        Index("ix_sessions_token_hash", "token_hash", unique=True),
    )


class Configuration(BaseModel):
    """Application configuration model."""

    __tablename__ = "configurations"

    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        *create_common_indexes("configurations"),
    )


class Task(BaseModel):
    """Background task model."""

    __tablename__ = "tasks"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(default=3, nullable=False)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        *create_common_indexes("tasks"),
        Index("ix_tasks_status_scheduled", "status", "scheduled_at"),
        Index("ix_tasks_name_status", "name", "status"),
    )


class WebhookEvent(BaseModel):
    """Webhook event model for outbound webhooks."""

    __tablename__ = "webhook_events"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(default=5, nullable=False)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    response_status: Mapped[Optional[int]] = mapped_column(nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        *create_common_indexes("webhook_events"),
        Index("ix_webhook_events_status_retry", "status", "next_retry_at"),
    )


class FeatureFlag(BaseModel):
    """Feature flag model."""

    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rules: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # Targeting rules
    variants: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # A/B variants
    environment: Mapped[str] = mapped_column(String(50), default="production", nullable=False)

    __table_args__ = (
        *create_common_indexes("feature_flags"),
        Index("ix_feature_flags_env_enabled", "environment", "enabled"),
    )