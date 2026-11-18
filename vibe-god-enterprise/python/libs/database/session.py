"""
Database Session Management
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from .core import get_database, Database


# Global session context for request-scoped sessions
_session_context: Optional[AsyncSession] = None


@asynccontextmanager
async def session_scope(read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session with automatic commit/rollback.

    Usage:
        async with session_scope() as session:
            user = await session.get(User, user_id)
            user.name = "New Name"
            # Auto-commits on success, rolls back on exception
    """
    db = await get_database()
    async with db.session(read_only=read_only) as session:
        yield session


@asynccontextmanager
async def transaction_scope(read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session with explicit transaction control.

    Usage:
        async with transaction_scope() as session:
            user = await session.get(User, user_id)
            user.name = "New Name"
            # Transaction committed on success, rolled back on exception
    """
    db = await get_database()
    async with db.transaction(read_only=read_only) as session:
        yield session


async def get_session(read_only: bool = False) -> AsyncSession:
    """
    Get a database session (for dependency injection).

    Note: Caller is responsible for closing the session.
    Prefer session_scope() or transaction_scope() for automatic management.
    """
    db = await get_database()
    return db._session_factory()


class SessionManager:
    """Manages request-scoped database sessions."""

    def __init__(self):
        self._session: Optional[AsyncSession] = None

    async def __aenter__(self) -> AsyncSession:
        db = await get_database()
        self._session = db._session_factory()
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            if exc_type:
                await self._session.rollback()
            else:
                await self._session.commit()
            await self._session.close()
            self._session = None

    @property
    def session(self) -> Optional[AsyncSession]:
        return self._session


# FastAPI dependency
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session."""
    async with session_scope() as session:
        yield session


async def get_db_read_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for read-only database session."""
    async with session_scope(read_only=True) as session:
        yield session


# Session utilities
async def execute_in_session(
    func,
    *args,
    read_only: bool = False,
    **kwargs,
) -> Any:
    """
    Execute a function within a database session.

    Args:
        func: Async function that takes session as first argument
        *args: Additional positional arguments
        read_only: Use read replica
        **kwargs: Additional keyword arguments

    Returns:
        Function result
    """
    async with session_scope(read_only=read_only) as session:
        return await func(session, *args, **kwargs)


async def execute_in_transaction(
    func,
    *args,
    read_only: bool = False,
    **kwargs,
) -> Any:
    """
    Execute a function within a database transaction.

    Args:
        func: Async function that takes session as first argument
        *args: Additional positional arguments
        read_only: Use read replica
        **kwargs: Additional keyword arguments

    Returns:
        Function result
    """
    async with transaction_scope(read_only=read_only) as session:
        return await func(session, *args, **kwargs)


# Bulk operations
async def bulk_insert(
    model_class,
    objects: list,
    batch_size: int = 1000,
) -> int:
    """
    Bulk insert objects.

    Args:
        model_class: SQLAlchemy model class
        objects: List of model instances or dicts
        batch_size: Batch size for inserts

    Returns:
        Number of inserted rows
    """
    from sqlalchemy.dialects.postgresql import insert

    db = await get_database()
    total = 0

    async with db.session() as session:
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]

            # Convert to dicts if needed
            if batch and hasattr(batch[0], "__table__"):
                batch = [obj.__dict__ for obj in batch]
                # Remove SQLAlchemy internal attributes
                for item in batch:
                    item.pop("_sa_instance_state", None)

            stmt = insert(model_class).values(batch)
            await session.execute(stmt)
            total += len(batch)

        await session.commit()

    return total


async def bulk_upsert(
    model_class,
    objects: list,
    conflict_columns: list,
    update_columns: list,
    batch_size: int = 1000,
) -> int:
    """
    Bulk upsert (insert or update) objects.

    Args:
        model_class: SQLAlchemy model class
        objects: List of dicts
        conflict_columns: Columns to check for conflicts
        update_columns: Columns to update on conflict
        batch_size: Batch size

    Returns:
        Number of affected rows
    """
    from sqlalchemy.dialects.postgresql import insert

    db = await get_database()
    total = 0

    async with db.session() as session:
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]

            stmt = insert(model_class).values(batch)

            # Build upsert
            update_dict = {col: stmt.excluded[col] for col in update_columns}
            stmt = stmt.on_conflict_do_update(
                index_elements=conflict_columns,
                set_=update_dict,
            )

            await session.execute(stmt)
            total += len(batch)

        await session.commit()

    return total