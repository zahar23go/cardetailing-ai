"""add_materials_warehouse

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-08-11 08:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "i9j0k1l2m3n4"
down_revision: Union[str, Sequence[str], None] = "h8i9j0k1l2m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "materials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sku", sa.String(100), nullable=True, comment="Артикул / SKU"),
        sa.Column(
            "category",
            sa.String(50),
            nullable=False,
            server_default="other",
            comment="chemistry, consumables, inventory, workwear, other",
        ),
        sa.Column(
            "unit",
            sa.String(20),
            nullable=False,
            server_default="pcs",
            comment="pcs, ml, l, g, kg, m, pack",
        ),
        sa.Column(
            "quantity",
            sa.Numeric(12, 3),
            nullable=False,
            server_default="0",
            comment="Текущий остаток",
        ),
        sa.Column(
            "min_quantity",
            sa.Numeric(12, 3),
            nullable=False,
            server_default="0",
            comment="Минимальный запас (порог алерта)",
        ),
        sa.Column(
            "purchase_price",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
            comment="Закупочная цена за единицу",
        ),
        sa.Column("supplier", sa.String(255), nullable=True, comment="Поставщик"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_materials_id", "materials", ["id"])
    op.create_index("ix_materials_tenant_id", "materials", ["tenant_id"])
    op.create_index("ix_materials_name", "materials", ["name"])
    op.create_index("ix_materials_sku", "materials", ["sku"])
    op.create_index("ix_materials_category", "materials", ["category"])
    op.create_index("ix_materials_is_active", "materials", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_materials_is_active", table_name="materials")
    op.drop_index("ix_materials_category", table_name="materials")
    op.drop_index("ix_materials_sku", table_name="materials")
    op.drop_index("ix_materials_name", table_name="materials")
    op.drop_index("ix_materials_tenant_id", table_name="materials")
    op.drop_index("ix_materials_id", table_name="materials")
    op.drop_table("materials")
