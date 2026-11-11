"""Add scheduled time fields

Revision ID: 73f3aaf3997c
Revises: 451eba5de621
Create Date: 2026-05-29 23:15:00.448363

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '73f3aaf3997c'
down_revision: Union[str, Sequence[str], None] = '451eba5de621'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tasks', sa.Column('scheduled_start', sa.DateTime(), nullable=True))
    op.add_column('tasks', sa.Column('scheduled_end', sa.DateTime(), nullable=True))
    op.drop_column('tasks', 'actual_time_minutes')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('tasks', sa.Column('actual_time_minutes', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_column('tasks', 'scheduled_end')
    op.drop_column('tasks', 'scheduled_start')
