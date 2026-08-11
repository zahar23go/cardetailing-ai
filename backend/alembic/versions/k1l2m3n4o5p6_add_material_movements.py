"""add_material_movements_inventory

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2026-08-11 11:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "k1l2m3n4o5p6"
down_revision: Union[str, Sequence[str], None] = "j0k1l2m3n4o5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "material_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "material_id",
            sa.Integer(),
            sa.ForeignKey("materials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "movement_type",
            sa.String(20),
            nullable=False,
            comment="in, out, adjust, initial",
        ),
        sa.Column("delta", sa.Numeric(12, 3), nullable=False, comment="Изменение остатка (+/−)"),
        sa.Column("quantity_before", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("quantity_after", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_material_movements_id", "material_movements", ["id"])
    op.create_index("ix_material_movements_tenant_id", "material_movements", ["tenant_id"])
    op.create_index("ix_material_movements_material_id", "material_movements", ["material_id"])
    op.create_index("ix_material_movements_movement_type", "material_movements", ["movement_type"])
    op.create_index("ix_material_movements_created_by_id", "material_movements", ["created_by_id"])
    op.create_index("ix_material_movements_created_at", "material_movements", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_material_movements_created_at", table_name="material_movements")
    op.drop_index("ix_material_movements_created_by_id", table_name="material_movements")
    op.drop_index("ix_material_movements_movement_type", table_name="material_movements")
    op.drop_index("ix_material_movements_material_id", table_name="material_movements")
    op.drop_index("ix_material_movements_tenant_id", table_name="material_movements")
    op.drop_index("ix_material_movements_id", table_name="material_movements")
    op.drop_table("material_movements")
