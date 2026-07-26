"""change_happy_hours_to_time_slot

Replace start_date/end_date with slot_start/slot_end (Time columns)
for happy hours time-slot-based discounts.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-20 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove old date columns
    op.drop_column('discount_rules', 'start_date')
    op.drop_column('discount_rules', 'end_date')
    # Add new time slot columns
    op.add_column('discount_rules', sa.Column(
        'slot_start', sa.Time(),
        nullable=True,
        comment='Время начала слота (HH:MM)',
    ))
    op.add_column('discount_rules', sa.Column(
        'slot_end', sa.Time(),
        nullable=True,
        comment='Время конца слота (HH:MM)',
    ))


def downgrade() -> None:
    op.drop_column('discount_rules', 'slot_end')
    op.drop_column('discount_rules', 'slot_start')
    op.add_column('discount_rules', sa.Column(
        'start_date', sa.DateTime(timezone=True),
        nullable=True,
    ))
    op.add_column('discount_rules', sa.Column(
        'end_date', sa.DateTime(timezone=True),
        nullable=True,
    ))
