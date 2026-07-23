import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """
    Base generic repository class providing standard database query actions.
    Uses AsyncSession execution.
    """

    def __init__(self, model: type[T], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, id: uuid.UUID) -> T | None:
        """Fetch a single record by its UUID primary key."""
        from typing import Any

        model_cls: Any = self.model
        result = await self.session.execute(select(self.model).where(model_cls.id == str(id)))
        return result.scalar_one_or_none()

    async def get_all(self, *, skip: int = 0, limit: int = 20) -> list[T]:
        """Fetch a list of records with offset pagination limits."""
        result = await self.session.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, obj: T) -> T:
        """Add a new object instance to the session."""
        self.session.add(obj)
        return obj

    async def update(self, obj: T, *, update_data: dict[str, Any]) -> T:
        """Apply dynamic values to model and update attributes."""
        for field, value in update_data.items():
            if hasattr(obj, field):
                setattr(obj, field, value)
        self.session.add(obj)
        return obj

    async def delete(self, id: uuid.UUID) -> bool:
        """Remove a record by its identifier. Returns True if successful."""
        record = await self.get_by_id(id)
        if not record:
            return False
        await self.session.delete(record)
        return True
