"""add_service_id_client_id_to_discount_rules

Add service_id, client_id, valid_until to discount_rules.

Revision ID: d0e1f2a3b4c5
Revises: a7b8c9d0e1f2
Create Date: 2026-07-20 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('discount_rules', sa.Column(
        'service_id', sa.Integer(),
        sa.ForeignKey('services.id', ondelete='CASCADE'),
        nullable=True, index=True,
        comment='Привязка скидки к услуге',
    ))
    op.add_column('discount_rules', sa.Column(
        'client_id', sa.Integer(),
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=True, index=True,
        comment='Персональная скидка для клиента',
    ))
    op.add_column('discount_rules', sa.Column(
        'valid_until', sa.DateTime(timezone=True),
        nullable=True,
        comment='Срок действия скидки',
    ))


def downgrade() -> None:
    op.drop_column('discount_rules', 'valid_until')
    op.drop_column('discount_rules', 'client_id')
    op.drop_column('discount_rules', 'service_id')
