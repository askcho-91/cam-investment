"""create chat conversation tables

Revision ID: 82fb702cb1ba
Revises: c3d4e5f6a7b8
Create Date: 2026-09-13 03:04:19.975410

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "82fb702cb1ba"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "support_conversations",
        sa.Column(
            "id",
            sa.UUID(),
            default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", postgresql.TEXT(), nullable=False),
        sa.Column("last_interaction_id", postgresql.TEXT(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_foreign_key(
        "fk_support_conversations_user_id",
        "support_conversations",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "support_messages",
        sa.Column(
            "id",
            sa.UUID(),
            default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column(
            "role", postgresql.ENUM("bot", "user", name="message_role"), nullable=False
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_foreign_key(
        "fk_support_messages_conversation_id",
        "support_messages",
        "support_conversations",
        ["conversation_id"],
        ["id"],
        ondelete="CASCADE",
    )

def downgrade() -> None:
    """Downgrade schema."""
    pass
