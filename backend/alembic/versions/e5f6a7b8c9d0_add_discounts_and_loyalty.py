"""add_discounts_and_loyalty

Create discount_rules, client_discounts, loyalty_points tables.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-14 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- discount_rules ---
    op.create_table(
        'discount_rules',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False,
                  comment='happy_hours, frequency, win_back, cashback'),
        sa.Column('conditions', postgresql.JSONB, nullable=False,
                  server_default='{}'),
        sa.Column('discount_percent', sa.Integer(), nullable=False, default=0),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # --- client_discounts ---
    op.create_table(
        'client_discounts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('client_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('discount_rule_id', sa.Integer(),
                  sa.ForeignKey('discount_rules.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('appointment_id', sa.Integer(),
                  sa.ForeignKey('appointments.id', ondelete='SET NULL'),
                  nullable=True, index=True),
        sa.Column('applied_percent', sa.Integer(), nullable=False, default=0),
        sa.Column('applied_amount', sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column('is_used', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # --- loyalty_points ---
    op.create_table(
        'loyalty_points',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('client_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False, index=True, unique=True),
        sa.Column('balance', sa.Integer(), nullable=False, default=0),
        sa.Column('total_earned', sa.Integer(), nullable=False, default=0),
        sa.Column('total_spent', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('loyalty_points')
    op.drop_table('client_discounts')
    op.drop_table('discount_rules')
