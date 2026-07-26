"""fill box_id for existing appointments via box_services

Revision ID: c1d2e3f4a5b6
Revises: 717fae593cf9
Create Date: 2026-07-26 19:46:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = '717fae593cf9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fill box_id for appointments that have a matching service-to-box mapping."""
    op.execute("""
        UPDATE appointments
        SET box_id = box_services.box_id
        FROM box_services
        WHERE appointments.box_id IS NULL
          AND appointments.service_id = box_services.service_id
          AND appointments.tenant_id = box_services.tenant_id
    """)


def downgrade() -> None:
    """No downgrade needed — data migration only."""
    pass
