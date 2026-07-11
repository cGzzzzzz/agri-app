"""add asynchronous chat processing state

Revision ID: 0002_conversation_processing_status
Revises: 0001_initial
Create Date: 2026-07-11
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_conversation_processing_status"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("status", sa.String(length=20), nullable=False, server_default="completed"))
    op.add_column("conversations", sa.Column("error_message", sa.Text(), nullable=True))
    op.create_index(op.f("ix_conversations_status"), "conversations", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_conversations_status"), table_name="conversations")
    op.drop_column("conversations", "error_message")
    op.drop_column("conversations", "status")
