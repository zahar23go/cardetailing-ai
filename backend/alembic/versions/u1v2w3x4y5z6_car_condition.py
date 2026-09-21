"""Состояние авто для мастера: профиль авто + снимок на визит.

Revision ID: u1v2w3x4y5z6
Revises: t0u1v2w3x4y5
Create Date: 2026-09-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "u1v2w3x4y5z6"
down_revision: Union[str, Sequence[str], None] = "t0u1v2w3x4y5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cars", sa.Column("paint_type", sa.String(20), nullable=True))
    op.add_column(
        "cars",
        sa.Column(
            "glass_defects",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "cars",
        sa.Column(
            "care_requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("cars", sa.Column("condition_notes", sa.Text(), nullable=True))

    op.add_column(
        "appointments",
        sa.Column("car_condition", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("appointments", "car_condition")
    op.drop_column("cars", "condition_notes")
    op.drop_column("cars", "care_requirements")
    op.drop_column("cars", "glass_defects")
    op.drop_column("cars", "paint_type")
