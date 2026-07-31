"""add_service_cost_price_and_discount_recs

Revision ID: g7h8i9j0k1l2
Revises: c1d2e3f4a5b6
Create Date: 2026-07-31 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'g7h8i9j0k1l2'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'services',
        sa.Column(
            'cost_price',
            sa.Numeric(10, 2),
            nullable=False,
            server_default='0',
            comment='Себестоимость услуги',
        ),
    )
    # Если себестоимость не задана — подтянуть из материалов
    op.execute("UPDATE services SET cost_price = material_cost WHERE cost_price = 0 AND material_cost > 0")

    op.create_table(
        'service_discount_recommendations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('service_id', sa.Integer(), sa.ForeignKey('services.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('period_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('bookings_30d', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('bookings_prev_30d', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('popularity_index', sa.Float(), nullable=False, server_default='0'),
        sa.Column('margin_raw', sa.Float(), nullable=False, server_default='0'),
        sa.Column('margin_index', sa.Float(), nullable=False, server_default='0'),
        sa.Column('priority', sa.Float(), nullable=False, server_default='0'),
        sa.Column('suggested_percent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('scenario', sa.String(50), nullable=False, server_default='priority'),
        sa.Column('reason', sa.Text(), nullable=False, server_default=''),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending', index=True),
        sa.Column('adjusted_percent', sa.Integer(), nullable=True),
        sa.Column('discount_rule_id', sa.Integer(), sa.ForeignKey('discount_rules.id', ondelete='SET NULL'), nullable=True),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('service_discount_recommendations')
    op.drop_column('services', 'cost_price')
