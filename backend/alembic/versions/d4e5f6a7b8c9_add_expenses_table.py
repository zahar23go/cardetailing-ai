"""add_expenses_table

Create expenses table for P&L accounting.

Revision ID: d4e5f6a7b8c9
Revises: bc3a1e2f4d5e
Create Date: 2026-07-12 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'bc3a1e2f4d5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'expenses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('category', sa.String(50), nullable=False, server_default='other'),
        sa.Column('expense_date', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_expenses_id', 'expenses', ['id'])
    op.create_index('ix_expenses_tenant_id', 'expenses', ['tenant_id'])


def downgrade() -> None:
    op.drop_index('ix_expenses_tenant_id', table_name='expenses')
    op.drop_index('ix_expenses_id', table_name='expenses')
    op.drop_table('expenses')
