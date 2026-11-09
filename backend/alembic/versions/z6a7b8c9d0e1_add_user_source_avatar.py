"""CRM: источник привлечения и аватар клиента.

Revision ID: z6a7b8c9d0e1
Revises: y5z6a7b8c9d0
Create Date: 2026-11-09 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "z6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "y5z6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "source",
            sa.String(length=100),
            nullable=True,
            comment="Источник привлечения клиента",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "avatar",
            sa.String(length=500),
            nullable=True,
            comment="Ссылка на аватар клиента",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "avatar")
    op.drop_column("users", "source")
