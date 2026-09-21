"""Отзывы и ИИ-вердикт по качеству услуг.

Revision ID: v2w3x4y5z6a7
Revises: u1v2w3x4y5z6
Create Date: 2026-09-21 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v2w3x4y5z6a7"
down_revision: Union[str, Sequence[str], None] = "u1v2w3x4y5z6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("external_id", sa.String(100), nullable=True),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "source", "external_id",
            name="uq_reviews_tenant_source_external",
        ),
    )
    op.create_index("ix_reviews_tenant_id", "reviews", ["tenant_id"])
    op.create_index("ix_reviews_external_id", "reviews", ["external_id"])

    op.create_table(
        "review_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reviews_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("average_rating", sa.Float(), nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="ai"),
        sa.Column(
            "verdict",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_review_analyses_tenant_id", "review_analyses", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_review_analyses_tenant_id", table_name="review_analyses")
    op.drop_table("review_analyses")
    op.drop_index("ix_reviews_external_id", table_name="reviews")
    op.drop_index("ix_reviews_tenant_id", table_name="reviews")
    op.drop_table("reviews")
