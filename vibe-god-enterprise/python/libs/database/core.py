"""
Database Core - SQLAlchemy Integration with Connection Pooling
"""
import os
import logging
from typing import Optional, AsyncGenerator, Dict, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import event, text, MetaData
from sqlalchemy.exc import SQLAlchemyError

from .models import Base

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration."""
    host: str = "localhost"
    port: int = 5432
    username: str = "postgres"
    password: str = "postgres"
    database: str = "vibe_god"
    schema: str = "public"

    # Connection pool
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: float = 30.0
    pool_recycle: int = 3600  # 1 hour
    pool_pre_ping: bool = True

    # Engine
    echo: bool = False
    echo_pool: bool = False
    future: bool = True

    # SSL
    ssl_mode: str = "prefer"  # disable, allow, prefer, require, verify-ca, verify-full
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    ssl_root_cert: Optional[str] = None

    # Read replica (optional)
    read_replica_host: Optional[str] = None
    read_replica_port: Optional[int] = None

    @property
    def url(self) -> str:
        """Generate async database URL."""
        base_url = f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        params = []
        if self.ssl_mode != "disable":
            params.append(f"sslmode={self.ssl_mode}")
        if self.ssl_cert:
            params.append(f"sslcert={self.ssl_cert}")
        if self.ssl_key:
            params.append(f"sslkey={self.ssl_key}")
        if self.ssl_root_cert:
            params.append(f"sslrootcert={self.ssl_root_cert}")
        if self.schema:
            params.append(f"options=-csearch_path%3D{self.schema}")

        if params:
            return f"{base_url}?{'&'.join(params)}"
        return base_url

    @property
    def read_replica_url(self) -> Optional[str]:
        """Generate read replica URL if configured."""
        if not self.read_replica_host:
            return None

        port = self.read_replica_port or self.port
        base_url = f"postgresql+asyncpg://{self.username}:{self.password}@{self.read_replica_host}:{port}/{self.database}"
        params = []
        if self.ssl_mode != "disable":
            params.append(f"sslmode={self.ssl_mode}")
        if params:
            return f"{base_url}?{'&'.join(params)}"
        return base_url


class Database:
    """
    Database manager with connection pooling, read replicas, and health checks.
    """

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._engine: Optional[AsyncEngine] = None
        self._read_engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._read_session_factory: Optional[async_sessionmaker] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize database engines and session factories."""
        if self._initialized:
            return

        # Create main engine
        self._engine = create_async_engine(
            self.config.url,
            poolclass=QueuePool,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_timeout=self.config.pool_timeout,
            pool_recycle=self.config.pool_recycle,
            pool_pre_ping=self.config.pool_pre_ping,
            echo=self.config.echo,
            echo_pool=self.config.echo_pool,
            future=self.config.future,
        )

        # Create read replica engine if configured
        if self.config.read_replica_url:
            self._read_engine = create_async_engine(
                self.config.read_replica_url,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                pool_pre_ping=self.config.pool_pre_ping,
                echo=self.config.echo,
                future=self.config.future,
            )

        # Create session factories
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False,
        )

        if self._read_engine:
            self._read_session_factory = async_sessionmaker(
                self._read_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False,
            )

        # Set up event listeners
        self._setup_event_listeners()

        # Test connection
        await self.health_check()

        self._initialized = True
        logger.info("Database initialized successfully")

    def _setup_event_listeners(self) -> None:
        """Set up SQLAlchemy event listeners."""

        @event.listens_for(self._engine.sync_engine, "connect")
        def set_search_path(dbapi_connection, connection_record):
            """Set search path on connect."""
            if self.config.schema:
                cursor = dbapi_connection.cursor()
                cursor.execute(f"SET search_path TO {self.config.schema}")
                cursor.close()

        @event.listens_for(self._engine.sync_engine, "checkout")
        def ping_connection(dbapi_connection, connection_record, connection_proxy):
            """Ping connection on checkout to detect stale connections."""
            try:
                cursor = dbapi_connection.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
            except Exception:
                # Connection is stale, raise to trigger reconnect
                raise SQLAlchemyError("Stale connection detected")

    @asynccontextmanager
    async def session(self, read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session.

        Args:
            read_only: If True, use read replica (if available)

        Yields:
            AsyncSession
        """
        if not self._initialized:
            await self.initialize()

        # Use read replica for read-only operations if available
        factory = self._session_factory
        if read_only and self._read_session_factory:
            factory = self._read_session_factory

        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    @asynccontextmanager
    async def transaction(self, read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session with explicit transaction control.

        Args:
            read_only: If True, use read replica

        Yields:
            AsyncSession
        """
        if not self._initialized:
            await self.initialize()

        factory = self._session_factory
        if read_only and self._read_session_factory:
            factory = self._read_session_factory

        async with factory() as session:
            async with session.begin():
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise

    async def execute_raw(self, query: str, params: Optional[Dict] = None, read_only: bool = False) -> Any:
        """Execute raw SQL query."""
        async with self.session(read_only=read_only) as session:
            result = await session.execute(text(query), params or {})
            return result

    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            if not self._engine:
                return False
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status."""
        if not self._engine:
            return {}

        pool = self._engine.pool
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total": pool.size() + pool.overflow(),
        }

    async def create_tables(self) -> None:
        """Create all tables (for development/testing)."""
        if not self._engine:
            await self.initialize()

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

    async def drop_tables(self) -> None:
        """Drop all tables (for testing)."""
        if not self._engine:
            await self.initialize()

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped")

    async def close(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None

        if self._read_engine:
            await self._read_engine.dispose()
            self._read_engine = None

        self._initialized = False
        logger.info("Database connections closed")

    @property
    def engine(self) -> Optional[AsyncEngine]:
        return self._engine

    @property
    def read_engine(self) -> Optional[AsyncEngine]:
        return self._read_engine


# Global database instance
_database: Optional[Database] = None


async def get_database() -> Database:
    """Get or create global database instance."""
    global _database
    if _database is None:
        _database = Database(DatabaseConfig())
        await _database.initialize()
    return _database


async def init_database(config: Optional[DatabaseConfig] = None) -> Database:
    """Initialize database with custom config."""
    global _database
    if config is None:
        config = DatabaseConfig()
    _database = Database(config)
    await _database.initialize()
    return _database


async def close_database() -> None:
    """Close global database."""
    global _database
    if _database:
        await _database.close()
        _database = None