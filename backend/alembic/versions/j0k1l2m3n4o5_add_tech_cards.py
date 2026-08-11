"""add_tech_cards

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-08-11 11:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "j0k1l2m3n4o5"
down_revision: Union[str, Sequence[str], None] = "i9j0k1l2m3n4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tech_cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "service_id",
            sa.Integer(),
            sa.ForeignKey("services.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=True, comment="Название техкарты"),
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
        sa.UniqueConstraint("tenant_id", "service_id", name="uq_tech_cards_tenant_service"),
    )
    op.create_index("ix_tech_cards_id", "tech_cards", ["id"])
    op.create_index("ix_tech_cards_tenant_id", "tech_cards", ["tenant_id"])
    op.create_index("ix_tech_cards_service_id", "tech_cards", ["service_id"])
    op.create_index("ix_tech_cards_is_active", "tech_cards", ["is_active"])

    op.create_table(
        "tech_card_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tech_card_id",
            sa.Integer(),
            sa.ForeignKey("tech_cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "material_id",
            sa.Integer(),
            sa.ForeignKey("materials.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "quantity",
            sa.Numeric(12, 3),
            nullable=False,
            server_default="0",
            comment="Расход материала на одну услугу",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("tech_card_id", "material_id", name="uq_tech_card_items_card_material"),
    )
    op.create_index("ix_tech_card_items_id", "tech_card_items", ["id"])
    op.create_index("ix_tech_card_items_tech_card_id", "tech_card_items", ["tech_card_id"])
    op.create_index("ix_tech_card_items_material_id", "tech_card_items", ["material_id"])


def downgrade() -> None:
    op.drop_index("ix_tech_card_items_material_id", table_name="tech_card_items")
    op.drop_index("ix_tech_card_items_tech_card_id", table_name="tech_card_items")
    op.drop_index("ix_tech_card_items_id", table_name="tech_card_items")
    op.drop_table("tech_card_items")
    op.drop_index("ix_tech_cards_is_active", table_name="tech_cards")
    op.drop_index("ix_tech_cards_service_id", table_name="tech_cards")
    op.drop_index("ix_tech_cards_tenant_id", table_name="tech_cards")
    op.drop_index("ix_tech_cards_id", table_name="tech_cards")
    op.drop_table("tech_cards")
