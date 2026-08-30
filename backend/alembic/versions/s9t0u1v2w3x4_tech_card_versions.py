"""Версии техкарт.

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
Create Date: 2026-08-30 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "s9t0u1v2w3x4"
down_revision: Union[str, Sequence[str], None] = "r8s9t0u1v2w3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tech_cards",
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "tech_card_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tech_card_id",
            sa.Integer(),
            sa.ForeignKey("tech_cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tech_card_id", "version_no", name="uq_tech_card_versions_card_no"),
    )
    op.create_index("ix_tech_card_versions_tenant_id", "tech_card_versions", ["tenant_id"])
    op.create_index("ix_tech_card_versions_tech_card_id", "tech_card_versions", ["tech_card_id"])


def downgrade() -> None:
    op.drop_index("ix_tech_card_versions_tech_card_id", table_name="tech_card_versions")
    op.drop_index("ix_tech_card_versions_tenant_id", table_name="tech_card_versions")
    op.drop_table("tech_card_versions")
    op.drop_column("tech_cards", "current_version")
