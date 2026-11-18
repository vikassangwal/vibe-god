"""
Base Repository Pattern for Database Operations
"""
from typing import TypeVar, Generic, Type, Optional, List, Any, Dict
from uuid import UUID
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import BaseModel, SoftDeleteModel
from .session import session_scope, transaction_scope

ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations.

    Provides:
    - Create, Read, Update, Delete
    - Soft delete support
    - Pagination
    - Filtering
    - Bulk operations
    """

    def __init__(self, model: Type[ModelType], session: Optional[AsyncSession] = None):
        self.model = model
        self._session = session
        self._owns_session = session is None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("Repository not initialized with session")
        return self._session

    async def __aenter__(self):
        if self._owns_session:
            self._session = (await get_database())._session_factory()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._owns_session and self._session:
            if exc_type:
                await self._session.rollback()
            else:
                await self._session.commit()
            await self._session.close()
            self._session = None

    # ============ Create ============

    async def create(self, obj: ModelType) -> ModelType:
        """Create a new object."""
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def create_from_dict(self, data: Dict[str, Any]) -> ModelType:
        """Create object from dictionary."""
        obj = self.model(**data)
        return await self.create(obj)

    async def bulk_create(self, objects: List[ModelType]) -> List[ModelType]:
        """Bulk create objects."""
        self.session.add_all(objects)
        await self.session.flush()
        for obj in objects:
            await self.session.refresh(obj)
        return objects

    # ============ Read ============

    async def get_by_id(self, id: UUID, load_relations: bool = False) -> Optional[ModelType]:
        """Get object by ID."""
        query = select(self.model).where(self.model.id == id)

        if load_relations:
            # Load all relationships
            for rel in self.model.__mapper__.relationships:
                query = query.options(selectinload(getattr(self.model, rel.key)))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: List[UUID]) -> List[ModelType]:
        """Get multiple objects by IDs."""
        if not ids:
            return []
        query = select(self.model).where(self.model.id.in_(ids))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_one(self, *filters) -> Optional[ModelType]:
        """Get single object matching filters."""
        query = select(self.model).where(*filters)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *filters,
        offset: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        load_relations: bool = False,
    ) -> List[ModelType]:
        """Get all objects matching filters with pagination."""
        query = select(self.model).where(*filters)

        if load_relations:
            for rel in self.model.__mapper__.relationships:
                query = query.options(selectinload(getattr(self.model, rel.key)))

        if order_by:
            if order_by.startswith("-"):
                query = query.order_by(getattr(self.model, order_by[1:]).desc())
            else:
                query = query.order_by(getattr(self.model, order_by).asc())

        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, *filters) -> int:
        """Count objects matching filters."""
        query = select(func.count()).select_from(self.model).where(*filters)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def exists(self, *filters) -> bool:
        """Check if any object matches filters."""
        query = select(func.count()).select_from(self.model).where(*filters).limit(1)
        result = await self.session.execute(query)
        return (result.scalar() or 0) > 0

    # ============ Update ============

    async def update(self, obj: ModelType, data: Dict[str, Any]) -> ModelType:
        """Update object with data."""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update_by_id(self, id: UUID, data: Dict[str, Any]) -> Optional[ModelType]:
        """Update object by ID."""
        obj = await self.get_by_id(id)
        if obj:
            return await self.update(obj, data)
        return None

    async def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """Bulk update objects."""
        if not updates:
            return 0

        # Extract IDs
        ids = [u.pop("id") for u in updates if "id" in u]
        if not ids:
            return 0

        # Build update statement
        stmt = update(self.model).where(self.model.id.in_(ids))

        # This is a simplified version - in practice you'd use CASE statements
        # for different values per row, or execute individual updates
        count = 0
        for update_data in updates:
            obj_id = update_data.pop("id", None)
            if obj_id:
                stmt = update(self.model).where(self.model.id == obj_id).values(**update_data)
                result = await self.session.execute(stmt)
                count += result.rowcount

        return count

    # ============ Delete ============

    async def delete(self, obj: ModelType) -> bool:
        """Delete object (hard delete)."""
        await self.session.delete(obj)
        await self.session.flush()
        return True

    async def delete_by_id(self, id: UUID) -> bool:
        """Delete object by ID."""
        obj = await self.get_by_id(id)
        if obj:
            await self.delete(obj)
            return True
        return False

    async def soft_delete(self, obj: ModelType) -> bool:
        """Soft delete object (if model supports it)."""
        if isinstance(obj, SoftDeleteModel):
            obj.soft_delete()
            await self.session.flush()
            return True
        return False

    async def soft_delete_by_id(self, id: UUID) -> bool:
        """Soft delete object by ID."""
        obj = await self.get_by_id(id)
        if obj:
            return await self.soft_delete(obj)
        return False

    async def restore(self, obj: ModelType) -> bool:
        """Restore soft-deleted object."""
        if isinstance(obj, SoftDeleteModel):
            obj.restore()
            await self.session.flush()
            return True
        return False

    async def bulk_delete(self, ids: List[UUID]) -> int:
        """Bulk delete objects by IDs."""
        if not ids:
            return 0
        stmt = delete(self.model).where(self.model.id.in_(ids))
        result = await self.session.execute(stmt)
        return result.rowcount

    # ============ Query Helpers ============

    async def paginate(
        self,
        page: int = 1,
        page_size: int = 20,
        *filters,
        order_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated results."""
        offset = (page - 1) * page_size
        items = await self.get_all(*filters, offset=offset, limit=page_size, order_by=order_by)
        total = await self.count(*filters)

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
            "has_next": page * page_size < total,
            "has_prev": page > 1,
        }

    async def search(
        self,
        query: str,
        search_fields: List[str],
        *filters,
        offset: int = 0,
        limit: int = 100,
    ) -> List[ModelType]:
        """Full-text search across specified fields."""
        if not query or not search_fields:
            return await self.get_all(*filters, offset=offset, limit=limit)

        # Build ILIKE conditions for each field
        conditions = []
        for field in search_fields:
            if hasattr(self.model, field):
                column = getattr(self.model, field)
                conditions.append(column.ilike(f"%{query}%"))

        if conditions:
            search_filter = or_(*conditions)
            all_filters = list(filters) + [search_filter]
            return await self.get_all(*all_filters, offset=offset, limit=limit)

        return await self.get_all(*filters, offset=offset, limit=limit)

    # ============ Soft Delete Helpers ============

    def _active_filter(self):
        """Get filter for active (non-deleted) records."""
        if issubclass(self.model, SoftDeleteModel):
            return self.model.is_deleted == False
        return True

    async def get_active_by_id(self, id: UUID) -> Optional[ModelType]:
        """Get active object by ID."""
        return await self.get_by_id(id, load_relations=False)

    async def get_active_all(self, *filters, **kwargs) -> List[ModelType]:
        """Get all active objects."""
        all_filters = list(filters) + [self._active_filter()]
        return await self.get_all(*all_filters, **kwargs)

    async def count_active(self, *filters) -> int:
        """Count active objects."""
        all_filters = list(filters) + [self._active_filter()]
        return await self.count(*all_filters)


# Convenience functions for session management
async def get_repository(
    model: Type[ModelType],
    session: Optional[AsyncSession] = None,
) -> BaseRepository[ModelType]:
    """Get repository instance."""
    return BaseRepository(model, session)


# Specialized repositories
class UserRepository(BaseRepository[ModelType]):
    """User-specific repository."""

    async def get_by_email(self, email: str) -> Optional[ModelType]:
        return await self.get_one(self.model.email == email)

    async def get_by_username(self, username: str) -> Optional[ModelType]:
        return await self.get_one(self.model.username == username)

    async def get_active_users(self, **kwargs) -> List[ModelType]:
        return await self.get_active_all(self.model.status == "active", **kwargs)


class AuditLogRepository(BaseRepository[ModelType]):
    """Audit log repository."""

    async def log(
        self,
        action: str,
        resource_type: str,
        user_id: Optional[UUID] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict] = None,
        **kwargs
    ) -> ModelType:
        """Create audit log entry."""
        data = {
            "action": action,
            "resource_type": resource_type,
            "user_id": user_id,
            "resource_id": resource_id,
            "details": details or {},
            **kwargs,
        }
        return await self.create_from_dict(data)

    async def get_user_activity(
        self,
        user_id: UUID,
        limit: int = 100,
    ) -> List[ModelType]:
        return await self.get_all(
            self.model.user_id == user_id,
            order_by="-created_at",
            limit=limit,
        )

    async def get_resource_history(
        self,
        resource_type: str,
        resource_id: str,
    ) -> List[ModelType]:
        return await self.get_all(
            self.model.resource_type == resource_type,
            self.model.resource_id == resource_id,
            order_by="-created_at",
        )


class TaskRepository(BaseRepository[ModelType]):
    """Task repository."""

    async def get_pending_tasks(self, limit: int = 100) -> List[ModelType]:
        return await self.get_all(
            self.model.status == "pending",
            self.model.scheduled_at <= func.now(),
            order_by="scheduled_at",
            limit=limit,
        )

    async def claim_task(self, task_id: UUID, worker_id: str) -> Optional[ModelType]:
        """Atomically claim a task."""
        async with transaction_scope() as session:
            repo = BaseRepository(self.model, session)
            task = await repo.get_by_id(task_id)
            if task and task.status == "pending":
                task.status = "running"
                task.worker_id = worker_id
                task.started_at = func.now()
                await session.flush()
                await session.refresh(task)
                return task
        return None

    async def complete_task(self, task_id: UUID, result: Dict) -> bool:
        async with transaction_scope() as session:
            repo = BaseRepository(self.model, session)
            task = await repo.get_by_id(task_id)
            if task:
                task.status = "completed"
                task.result = result
                task.completed_at = func.now()
                return True
        return False

    async def fail_task(self, task_id: UUID, error: str) -> bool:
        async with transaction_scope() as session:
            repo = BaseRepository(self.model, session)
            task = await repo.get_by_id(task_id)
            if task:
                task.retry_count += 1
                task.error = error
                if task.retry_count >= task.max_retries:
                    task.status = "failed"
                else:
                    task.status = "pending"
                return True
        return False