"""add_tech_card_blocks

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2026-08-18 13:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "m3n4o5p6q7r8"
down_revision: Union[str, Sequence[str], None] = "l2m3n4o5p6q7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tech_card_blocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tech_card_id",
            sa.Integer(),
            sa.ForeignKey("tech_cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("photo_url", sa.Text(), nullable=True),
    )
    op.create_index("ix_tech_card_blocks_id", "tech_card_blocks", ["id"])
    op.create_index("ix_tech_card_blocks_tech_card_id", "tech_card_blocks", ["tech_card_id"])

    op.add_column(
        "tech_card_items",
        sa.Column(
            "block_id",
            sa.Integer(),
            sa.ForeignKey("tech_card_blocks.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_tech_card_items_block_id", "tech_card_items", ["block_id"])

    op.drop_constraint("uq_tech_card_items_card_material", "tech_card_items", type_="unique")

    conn = op.get_bind()
    cards = conn.execute(sa.text("SELECT id FROM tech_cards")).fetchall()
    for (card_id,) in cards:
        items = conn.execute(
            sa.text(
                "SELECT id FROM tech_card_items "
                "WHERE tech_card_id = :cid AND block_id IS NULL"
            ),
            {"cid": card_id},
        ).fetchall()
        if not items:
            continue
        block_id = conn.execute(
            sa.text(
                "INSERT INTO tech_card_blocks "
                "(tech_card_id, sort_order, title, duration_minutes) "
                "VALUES (:cid, 0, 'Материалы', 0) RETURNING id"
            ),
            {"cid": card_id},
        ).scalar()
        conn.execute(
            sa.text(
                "UPDATE tech_card_items SET block_id = :bid "
                "WHERE tech_card_id = :cid AND block_id IS NULL"
            ),
            {"bid": block_id, "cid": card_id},
        )

    op.create_unique_constraint(
        "uq_tech_card_items_block_material",
        "tech_card_items",
        ["block_id", "material_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_tech_card_items_block_material", "tech_card_items", type_="unique")
    op.drop_index("ix_tech_card_items_block_id", table_name="tech_card_items")
    op.drop_column("tech_card_items", "block_id")
    op.drop_index("ix_tech_card_blocks_tech_card_id", table_name="tech_card_blocks")
    op.drop_index("ix_tech_card_blocks_id", table_name="tech_card_blocks")
    op.drop_table("tech_card_blocks")
    op.create_unique_constraint(
        "uq_tech_card_items_card_material",
        "tech_card_items",
        ["tech_card_id", "material_id"],
    )
