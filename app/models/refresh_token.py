import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, utcnow
from app.domain.enums import TokenType

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(Base, TimestampMixin):
    """
    ORM Model for the 'refresh_tokens' table.

    Inherits TimestampMixin.
    Used to track session lifecycles and support Single-Use Refresh Token Rotation with Token Families.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    family_id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        nullable=False,
        default=uuid.uuid4,
    )

    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    token_type: Mapped[TokenType] = mapped_column(
        SQLEnum(TokenType),
        nullable=False,
        default=TokenType.REFRESH,
        server_default=TokenType.REFRESH.value,
    )

    # Client Metadata Auditing
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("idx_refresh_user_id", "user_id"),
        Index("idx_refresh_token_hash", "token_hash"),
        Index("idx_refresh_family_id", "family_id"),
    )
