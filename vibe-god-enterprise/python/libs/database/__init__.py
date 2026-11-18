"""
Enterprise Database Library for Vibe-God
Provides SQLAlchemy integration with migrations, connection pooling, and resilience.
"""

from .core import Database, DatabaseConfig, get_database
from .models import Base, TimestampMixin, SoftDeleteMixin
from .session import get_session, session_scope
from .migrations import MigrationManager, run_migrations
from .repository import BaseRepository

__all__ = [
    "Database",
    "DatabaseConfig",
    "get_database",
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "get_session",
    "session_scope",
    "MigrationManager",
    "run_migrations",
    "BaseRepository",
]