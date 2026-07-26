"""add_photo_service_id_and_description

Add service_id FK and description column to photos table
for portfolio-service binding.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-20 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add service_id FK to photos table
    op.add_column('photos', sa.Column(
        'service_id', sa.Integer(),
        sa.ForeignKey('services.id', ondelete='SET NULL'),
        nullable=True, index=True,
        comment='Привязка к услуге (для портфолио)',
    ))
    # Add description column to photos table
    op.add_column('photos', sa.Column(
        'description', sa.Text(),
        nullable=True,
        comment='Описание работы (было → стало)',
    ))


def downgrade() -> None:
    op.drop_column('photos', 'description')
    op.drop_column('photos', 'service_id')
