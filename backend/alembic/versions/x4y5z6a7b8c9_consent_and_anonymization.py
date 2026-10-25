"""152-ФЗ: согласие на обработку ПДн и обезличивание клиента.

Revision ID: x4y5z6a7b8c9
Revises: w3x4y5z6a7b8
Create Date: 2026-10-25 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "x4y5z6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "w3x4y5z6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "consent_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="152-ФЗ: когда пользователь дал согласие на обработку ПДн",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "consent_version",
            sa.String(length=20),
            nullable=True,
            comment="Версия политики конфиденциальности на момент согласия",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "anonymized_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="152-ФЗ: когда данные клиента обезличены (право на забвение)",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "anonymized_at")
    op.drop_column("users", "consent_version")
    op.drop_column("users", "consent_at")
