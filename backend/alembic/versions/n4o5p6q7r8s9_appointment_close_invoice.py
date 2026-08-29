"""appointment close invoice, steps, materials, movement link

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2026-08-29 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "n4o5p6q7r8s9"
down_revision: Union[str, Sequence[str], None] = "m3n4o5p6q7r8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "appointment_invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "appointment_id",
            sa.Integer(),
            sa.ForeignKey("appointments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "box_id",
            sa.Integer(),
            sa.ForeignKey("boxes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "service_id",
            sa.Integer(),
            sa.ForeignKey("services.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("service_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("discount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("material_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("catalog_material_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("shortage_qty_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("gross_profit", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column(
            "closed_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "closed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_appointment_invoices_id", "appointment_invoices", ["id"])
    op.create_index("ix_appointment_invoices_tenant_id", "appointment_invoices", ["tenant_id"])
    op.create_index(
        "ix_appointment_invoices_appointment_id",
        "appointment_invoices",
        ["appointment_id"],
        unique=True,
    )
    op.create_index("ix_appointment_invoices_box_id", "appointment_invoices", ["box_id"])

    op.create_table(
        "appointment_close_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "invoice_id",
            sa.Integer(),
            sa.ForeignKey("appointment_invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("block_id", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("done", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_appointment_close_steps_id", "appointment_close_steps", ["id"])
    op.create_index(
        "ix_appointment_close_steps_invoice_id",
        "appointment_close_steps",
        ["invoice_id"],
    )

    op.create_table(
        "appointment_close_materials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "invoice_id",
            sa.Integer(),
            sa.ForeignKey("appointment_invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "material_id",
            sa.Integer(),
            sa.ForeignKey("materials.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("unit", sa.String(20), nullable=False, server_default="pcs"),
        sa.Column("norm_qty", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("actual_qty", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("applied_qty", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("line_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("shortage", sa.Numeric(12, 3), nullable=False, server_default="0"),
    )
    op.create_index("ix_appointment_close_materials_id", "appointment_close_materials", ["id"])
    op.create_index(
        "ix_appointment_close_materials_invoice_id",
        "appointment_close_materials",
        ["invoice_id"],
    )

    op.add_column(
        "material_movements",
        sa.Column(
            "appointment_id",
            sa.Integer(),
            sa.ForeignKey("appointments.id", ondelete="SET NULL"),
            nullable=True,
            comment="Заезд, если расход при закрытии",
        ),
    )
    op.create_index(
        "ix_material_movements_appointment_id",
        "material_movements",
        ["appointment_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_material_movements_appointment_id", table_name="material_movements")
    op.drop_column("material_movements", "appointment_id")
    op.drop_index("ix_appointment_close_materials_invoice_id", table_name="appointment_close_materials")
    op.drop_index("ix_appointment_close_materials_id", table_name="appointment_close_materials")
    op.drop_table("appointment_close_materials")
    op.drop_index("ix_appointment_close_steps_invoice_id", table_name="appointment_close_steps")
    op.drop_index("ix_appointment_close_steps_id", table_name="appointment_close_steps")
    op.drop_table("appointment_close_steps")
    op.drop_index("ix_appointment_invoices_box_id", table_name="appointment_invoices")
    op.drop_index("ix_appointment_invoices_appointment_id", table_name="appointment_invoices")
    op.drop_index("ix_appointment_invoices_tenant_id", table_name="appointment_invoices")
    op.drop_index("ix_appointment_invoices_id", table_name="appointment_invoices")
    op.drop_table("appointment_invoices")
