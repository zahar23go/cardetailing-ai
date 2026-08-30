"""Навыки мастера и комиссия в чеке.

Revision ID: t0u1v2w3x4y5
Revises: s9t0u1v2w3x4
Create Date: 2026-08-30 10:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "t0u1v2w3x4y5"
down_revision: Union[str, Sequence[str], None] = "s9t0u1v2w3x4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("commission_percent", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "master_skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "master_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "service_id",
            sa.Integer(),
            sa.ForeignKey("services.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("commission_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("master_id", "service_id", name="uq_master_skills_master_service"),
    )
    op.create_index("ix_master_skills_tenant_id", "master_skills", ["tenant_id"])
    op.create_index("ix_master_skills_master_id", "master_skills", ["master_id"])
    op.create_index("ix_master_skills_service_id", "master_skills", ["service_id"])

    op.add_column(
        "appointment_invoices",
        sa.Column("commission_percent", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "appointment_invoices",
        sa.Column("commission_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("appointment_invoices", "commission_amount")
    op.drop_column("appointment_invoices", "commission_percent")
    op.drop_index("ix_master_skills_service_id", table_name="master_skills")
    op.drop_index("ix_master_skills_master_id", table_name="master_skills")
    op.drop_index("ix_master_skills_tenant_id", table_name="master_skills")
    op.drop_table("master_skills")
    op.drop_column("users", "commission_percent")
