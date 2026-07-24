"""add_reservations_table

Revision ID: 2010d89a6bf2
Revises: 1bd2d99cf989
Create Date: 2026-07-24 16:51:51.059122

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2010d89a6bf2'
down_revision: Union[str, None] = '1bd2d99cf989'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('reservations',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('member_id', sa.String(length=36), nullable=False),
    sa.Column('book_id', sa.String(length=36), nullable=False),
    sa.Column('reserved_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.Enum('PENDING', 'HOLD', 'COMPLETED', 'CANCELLED', 'EXPIRED', name='reservationstatus'), server_default='PENDING', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['member_id'], ['members.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_reservations_fifo', 'reservations', ['book_id', 'status', 'reserved_at'], unique=False)
    op.create_index('idx_reservations_member', 'reservations', ['member_id', 'status'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_reservations_member', table_name='reservations')
    op.drop_index('idx_reservations_fifo', table_name='reservations')
    op.drop_table('reservations')
