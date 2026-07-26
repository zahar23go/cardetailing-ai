"""merge heads

Revision ID: beb4da092f28
Revises: b2a020dd7c6e, d0e1f2a3b4c5
Create Date: 2026-07-20 19:20:28.213137

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'beb4da092f28'
down_revision: Union[str, Sequence[str], None] = ('b2a020dd7c6e', 'd0e1f2a3b4c5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
