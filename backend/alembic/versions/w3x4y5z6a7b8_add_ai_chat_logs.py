"""Аналитика диалогов: журнал ходов ИИ-ассистентов.

Revision ID: w3x4y5z6a7b8
Revises: v2w3x4y5z6a7
Create Date: 2026-10-17 07:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "w3x4y5z6a7b8"
down_revision: Union[str, Sequence[str], None] = "v2w3x4y5z6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_chat_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("assistant", sa.String(length=32), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column(
            "tool_calls",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_error", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ai_chat_logs_tenant_id", "ai_chat_logs", ["tenant_id"])
    op.create_index("ix_ai_chat_logs_user_id", "ai_chat_logs", ["user_id"])
    op.create_index("ix_ai_chat_logs_session_id", "ai_chat_logs", ["session_id"])
    op.create_index("ix_ai_chat_logs_assistant", "ai_chat_logs", ["assistant"])
    op.create_index("ix_ai_chat_logs_created_at", "ai_chat_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_chat_logs_created_at", table_name="ai_chat_logs")
    op.drop_index("ix_ai_chat_logs_assistant", table_name="ai_chat_logs")
    op.drop_index("ix_ai_chat_logs_session_id", table_name="ai_chat_logs")
    op.drop_index("ix_ai_chat_logs_user_id", table_name="ai_chat_logs")
    op.drop_index("ix_ai_chat_logs_tenant_id", table_name="ai_chat_logs")
    op.drop_table("ai_chat_logs")
