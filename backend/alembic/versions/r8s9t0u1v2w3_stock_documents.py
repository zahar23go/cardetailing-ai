"""Документы приёмки и ревизии склада.

Revision ID: r8s9t0u1v2w3
Revises: q7r8s9t0u1v2
Create Date: 2026-08-30 08:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "r8s9t0u1v2w3"
down_revision: Union[str, Sequence[str], None] = "q7r8s9t0u1v2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stock_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type", sa.String(length=20), nullable=False),
        sa.Column("document_no", sa.String(length=80), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("signed_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("signed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_stock_documents_tenant_id", "stock_documents", ["tenant_id"])
    op.create_index("ix_stock_documents_doc_type", "stock_documents", ["doc_type"])

    op.create_table(
        "stock_document_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("stock_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "material_id",
            sa.Integer(),
            sa.ForeignKey("materials.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("unit", sa.String(length=20), nullable=False, server_default="pcs"),
        sa.Column("system_qty", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("qty", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("delta", sa.Numeric(12, 3), nullable=False, server_default="0"),
    )
    op.create_index("ix_stock_document_lines_document_id", "stock_document_lines", ["document_id"])

    op.add_column(
        "material_movements",
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("stock_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_material_movements_document_id", "material_movements", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_material_movements_document_id", table_name="material_movements")
    op.drop_column("material_movements", "document_id")
    op.drop_index("ix_stock_document_lines_document_id", table_name="stock_document_lines")
    op.drop_table("stock_document_lines")
    op.drop_index("ix_stock_documents_doc_type", table_name="stock_documents")
    op.drop_index("ix_stock_documents_tenant_id", table_name="stock_documents")
    op.drop_table("stock_documents")
