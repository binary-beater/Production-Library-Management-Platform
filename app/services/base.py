"""Base Service class containing database session property definition."""

from sqlalchemy.ext.asyncio import AsyncSession


class BaseService:
    """Base service class encapsulating database session operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
