import datetime
from typing import Any

from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import BorrowStatus, MembershipStatus, ReservationStatus
from app.models.book import Book
from app.models.borrow_record import BorrowRecord
from app.models.member import Member
from app.models.reservation import Reservation


class DashboardRepository:
    """Read-only repository housing all database aggregate queries for operational metrics."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_inventory_summary(self) -> dict[str, int]:
        """Fetch total titles, total copies, checked out copies, and available shelf copies."""
        # 1. Total titles, copies, and available shelf copies (excluding soft-deleted books)
        inv_stmt = select(
            func.count(Book.id).label("total_titles"),
            func.coalesce(func.sum(Book.total_copies), 0).label("total_copies"),
            func.coalesce(func.sum(Book.available_copies), 0).label("available_copies"),
        ).where(Book.is_deleted == 0)

        inv_result = await self.session.execute(inv_stmt)
        inv_row = inv_result.fetchone()

        # 2. Currently checked out copies
        checkout_stmt = select(func.count(BorrowRecord.id)).where(
            BorrowRecord.status.in_(
                [BorrowStatus.BORROWED, BorrowStatus.RENEWED, BorrowStatus.OVERDUE]
            )
        )
        checkout_result = await self.session.execute(checkout_stmt)
        checked_out_copies = checkout_result.scalar_one_or_none() or 0

        if inv_row:
            return {
                "total_titles": inv_row.total_titles,
                "total_copies": int(inv_row.total_copies),
                "checked_out_copies": int(checked_out_copies),
                "available_copies": int(inv_row.available_copies),
            }
        return {
            "total_titles": 0,
            "total_copies": 0,
            "checked_out_copies": 0,
            "available_copies": 0,
        }

    async def get_member_summary(self) -> dict[str, int]:
        """Fetch counts of active and suspended members."""
        stmt = select(
            func.sum(case((Member.membership_status == MembershipStatus.ACTIVE, 1), else_=0)).label(
                "active"
            ),
            func.sum(
                case((Member.membership_status == MembershipStatus.SUSPENDED, 1), else_=0)
            ).label("suspended"),
        ).where(Member.is_deleted == 0)

        result = await self.session.execute(stmt)
        row = result.fetchone()

        active = 0
        suspended = 0
        if row:
            active = int(row.active or 0)
            suspended = int(row.suspended or 0)

        return {"active_count": active, "suspended_count": suspended}

    async def get_reservation_summary(self) -> dict[str, int]:
        """Fetch pending, hold, and expired today counts."""
        now = datetime.datetime.now(datetime.UTC)
        start_of_today = datetime.datetime.combine(
            now.date(), datetime.time.min, tzinfo=datetime.UTC
        )

        stmt = select(
            func.sum(case((Reservation.status == ReservationStatus.PENDING, 1), else_=0)).label(
                "pending"
            ),
            func.sum(case((Reservation.status == ReservationStatus.HOLD, 1), else_=0)).label(
                "hold"
            ),
            func.sum(
                case(
                    (
                        (Reservation.status == ReservationStatus.EXPIRED)
                        & (Reservation.updated_at >= start_of_today),
                        1,
                    ),
                    else_=0,
                )
            ).label("expired_today"),
        )

        result = await self.session.execute(stmt)
        row = result.fetchone()

        pending = 0
        hold = 0
        expired_today = 0
        if row:
            pending = int(row.pending or 0)
            hold = int(row.hold or 0)
            expired_today = int(row.expired_today or 0)

        return {"pending": pending, "hold": hold, "expired_today": expired_today}

    async def get_overdue_summary(self) -> dict[str, Any]:
        """Fetch count, ratio, and average days overdue for active checkouts."""
        now = datetime.datetime.now(datetime.UTC)

        # Total active checkouts
        active_stmt = select(func.count(BorrowRecord.id)).where(
            BorrowRecord.status.in_(
                [BorrowStatus.BORROWED, BorrowStatus.RENEWED, BorrowStatus.OVERDUE]
            )
        )
        active_res = await self.session.execute(active_stmt)
        total_active = active_res.scalar_one_or_none() or 0

        # Overdue borrows: either marked OVERDUE or past due date in BORROWED/RENEWED states
        overdue_stmt = select(
            func.count(BorrowRecord.id).label("count"),
            func.coalesce(
                func.avg(
                    func.timestampdiff(
                        text("day"),
                        BorrowRecord.due_date,
                        now,
                    )
                ),
                0.0,
            ).label("avg_days"),
        ).where(
            (BorrowRecord.status == BorrowStatus.OVERDUE)
            | (
                BorrowRecord.status.in_([BorrowStatus.BORROWED, BorrowStatus.RENEWED])
                & (BorrowRecord.due_date < now)
            )
        )

        overdue_res = await self.session.execute(overdue_stmt)
        overdue_row = overdue_res.fetchone()

        count = 0
        avg_days = 0.0
        if overdue_row:
            count = overdue_row.count or 0
            avg_days = float(overdue_row.avg_days or 0.0)
            # Ensure average is never negative (in case clocks drift slightly)
            if avg_days < 0:
                avg_days = 0.0

        ratio = 0.0
        if total_active > 0:
            ratio = round(count / total_active, 4)

        return {
            "count": count,
            "ratio": ratio,
            "average_days_overdue": round(avg_days, 2),
        }

    async def get_popular_books(self, days: int) -> list[dict[str, Any]]:
        """Fetch top 5 books with highest borrows in window, with tie-breaking."""
        now = datetime.datetime.now(datetime.UTC)
        start_of_window = now - datetime.timedelta(days=days)

        stmt = (
            select(
                Book.id.label("book_id"),
                Book.title.label("title"),
                Book.author.label("author"),
                func.count(BorrowRecord.id).label("checkout_count"),
            )
            .join(BorrowRecord, BorrowRecord.book_id == Book.id)
            .where(
                Book.is_deleted == 0,
                BorrowRecord.borrow_date >= start_of_window,
            )
            .group_by(Book.id, Book.title, Book.author)
            .order_by(
                text("checkout_count DESC"),
                Book.title.asc(),  # Deterministic tie-breaking
            )
            .limit(5)
        )

        result = await self.session.execute(stmt)
        return [
            {
                "book_id": row.book_id,
                "title": row.title,
                "author": row.author,
                "checkout_count": row.checkout_count,
            }
            for row in result.fetchall()
        ]

    async def get_borrow_velocity(self) -> dict[str, int]:
        """Fetch borrow transaction counts for: today, last 7 days, and last 30 days."""
        now = datetime.datetime.now(datetime.UTC)
        start_of_today = datetime.datetime.combine(
            now.date(), datetime.time.min, tzinfo=datetime.UTC
        )
        start_7_days = now - datetime.timedelta(days=7)
        start_30_days = now - datetime.timedelta(days=30)

        # We can run three fast scalar aggregate select statements
        today_stmt = select(func.count(BorrowRecord.id)).where(
            BorrowRecord.borrow_date >= start_of_today
        )
        days7_stmt = select(func.count(BorrowRecord.id)).where(
            BorrowRecord.borrow_date >= start_7_days
        )
        days30_stmt = select(func.count(BorrowRecord.id)).where(
            BorrowRecord.borrow_date >= start_30_days
        )

        today_res = await self.session.execute(today_stmt)
        days7_res = await self.session.execute(days7_stmt)
        days30_res = await self.session.execute(days30_stmt)

        return {
            "today": today_res.scalar_one_or_none() or 0,
            "last_7_days": days7_res.scalar_one_or_none() or 0,
            "last_30_days": days30_res.scalar_one_or_none() or 0,
        }
