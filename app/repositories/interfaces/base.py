import uuid
from typing import Any, Protocol, TypeVar

from app.db.base import Base

T = TypeVar("T", bound=Base)


class BaseRepositoryInterface(Protocol[T]):
    """Generic base interface repository protocol defining required CRUD actions."""

    async def get_by_id(self, id: uuid.UUID) -> T | None: ...

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[T]: ...

    async def create(self, obj: T) -> T: ...

    async def update(self, obj: T, *, update_data: dict[str, Any]) -> T: ...

    async def delete(self, id: uuid.UUID) -> bool: ...
