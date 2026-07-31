"""add_expense_accounting_fields

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-07-31 17:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'h8i9j0k1l2m3'
down_revision: Union[str, Sequence[str], None] = 'g7h8i9j0k1l2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('expenses', sa.Column('subcategory', sa.String(100), nullable=True))
    op.add_column(
        'expenses',
        sa.Column(
            'payment_status',
            sa.String(30),
            nullable=False,
            server_default='paid',
            comment='paid, unpaid, overdue, partial',
        ),
    )
    op.add_column(
        'expenses',
        sa.Column(
            'period_type',
            sa.String(30),
            nullable=False,
            server_default='monthly',
            comment='monthly, quarterly, yearly, one_time',
        ),
    )
    op.add_column('expenses', sa.Column('period_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('expenses', sa.Column('period_end', sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        'expenses',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('expenses', 'updated_at')
    op.drop_column('expenses', 'period_end')
    op.drop_column('expenses', 'period_start')
    op.drop_column('expenses', 'period_type')
    op.drop_column('expenses', 'payment_status')
    op.drop_column('expenses', 'subcategory')
