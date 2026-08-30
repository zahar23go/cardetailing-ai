"""VIN, кузов и пробег на карточке авто.

Revision ID: q7r8s9t0u1v2
Revises: p6q7r8s9t0u1
Create Date: 2026-08-30 08:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "q7r8s9t0u1v2"
down_revision: Union[str, Sequence[str], None] = "p6q7r8s9t0u1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cars", sa.Column("vin", sa.String(length=17), nullable=True))
    op.add_column("cars", sa.Column("body_type", sa.String(length=40), nullable=True))
    op.add_column("cars", sa.Column("mileage", sa.Integer(), nullable=True))
    op.create_index("ix_cars_vin", "cars", ["vin"])


def downgrade() -> None:
    op.drop_index("ix_cars_vin", table_name="cars")
    op.drop_column("cars", "mileage")
    op.drop_column("cars", "body_type")
    op.drop_column("cars", "vin")
