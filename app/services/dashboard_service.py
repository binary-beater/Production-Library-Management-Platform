import datetime
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.metrics import DASHBOARD_REQUESTS_TOTAL
from app.repositories.dashboard_repository import DashboardRepository
from app.services.base import BaseService


class DashboardService(BaseService):
    """Business service layer orchestrating aggregated operational metrics calculations."""

    def __init__(self, session: AsyncSession, dashboard_repo: DashboardRepository) -> None:
        super().__init__(session)
        self.dashboard_repo = dashboard_repo

    async def get_summary(self, days: int) -> dict[str, Any]:
        """Fetch all operational summaries, calculating SQL aggregations and capturing execution metrics."""
        start_time = time.perf_counter()
        DASHBOARD_REQUESTS_TOTAL.inc()

        # Execute queries sequentially to prevent multi-threading session access collisions
        inventory = await self.dashboard_repo.get_inventory_summary()
        members = await self.dashboard_repo.get_member_summary()
        reservations = await self.dashboard_repo.get_reservation_summary()
        overdue = await self.dashboard_repo.get_overdue_summary()
        popular_books = await self.dashboard_repo.get_popular_books(days)
        velocity = await self.dashboard_repo.get_borrow_velocity()

        elapsed = time.perf_counter() - start_time
        logger.info(
            "dashboard_metrics_compiled",
            days=days,
            elapsed_seconds=elapsed,
        )

        # Build response structure
        return {
            "inventory": inventory,
            "circulation": {
                "total_borrows_in_window": sum(b["checkout_count"] for b in popular_books),
                "borrowing_velocity": velocity,
            },
            "members": members,
            "reservations": reservations,
            "overdue": overdue,
            "popular_books": popular_books,
            "generated_at": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
