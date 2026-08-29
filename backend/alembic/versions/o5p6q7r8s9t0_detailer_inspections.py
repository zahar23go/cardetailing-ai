"""AI detailer inspections

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-08-29 17:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "o5p6q7r8s9t0"
down_revision: Union[str, Sequence[str], None] = "n4o5p6q7r8s9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "detailer_inspections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "car_id",
            sa.Integer(),
            sa.ForeignKey("cars.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "appointment_id",
            sa.Integer(),
            sa.ForeignKey("appointments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "primary_service_id",
            sa.Integer(),
            sa.ForeignKey("services.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "suggested_box_id",
            sa.Integer(),
            sa.ForeignKey("boxes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("master_brief", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("findings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("upsells", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("slots", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("photo_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_detailer_inspections_id", "detailer_inspections", ["id"])
    op.create_index("ix_detailer_inspections_tenant_id", "detailer_inspections", ["tenant_id"])
    op.create_index("ix_detailer_inspections_client_id", "detailer_inspections", ["client_id"])
    op.create_index("ix_detailer_inspections_car_id", "detailer_inspections", ["car_id"])
    op.create_index("ix_detailer_inspections_appointment_id", "detailer_inspections", ["appointment_id"])


def downgrade() -> None:
    op.drop_index("ix_detailer_inspections_appointment_id", table_name="detailer_inspections")
    op.drop_index("ix_detailer_inspections_car_id", table_name="detailer_inspections")
    op.drop_index("ix_detailer_inspections_client_id", table_name="detailer_inspections")
    op.drop_index("ix_detailer_inspections_tenant_id", table_name="detailer_inspections")
    op.drop_index("ix_detailer_inspections_id", table_name="detailer_inspections")
    op.drop_table("detailer_inspections")
