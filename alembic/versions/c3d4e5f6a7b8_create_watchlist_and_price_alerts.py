"""create watchlist and price alerts

Revision ID: c3d4e5f6a7b8
Revises: 00f1cac8ffde
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "00f1cac8ffde"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Define PostgreSQL Enum types
    asset_type_enum = postgresql.ENUM(
        "ng_stock",
        "global_stock",
        "forex",
        "crypto",
        "commodity",
        "etf",
        "mutual_fund",
        "index",
        name="asset_type",
        create_type=False,
    )
    alert_direction_enum = postgresql.ENUM(
        "above", "below", name="alert_direction", create_type=False
    )

    # Safely create enum types in DB if they don't exist yet
    asset_type_enum.create(bind, checkfirst=True)
    alert_direction_enum.create(bind, checkfirst=True)

    op.create_table(
        "watchlist_items",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("asset_type", asset_type_enum, nullable=False),
        sa.Column("identifier", sa.Text(), nullable=False),
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "asset_type",
            "identifier",
            name="uq_watchlist_user_asset",
        ),
    )
    op.create_index("ix_watchlist_items_user_id", "watchlist_items", ["user_id"])

    op.create_table(
        "price_alerts",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("asset_type", asset_type_enum, nullable=False),
        sa.Column("identifier", sa.Text(), nullable=False),
        sa.Column("direction", alert_direction_enum, nullable=False),
        sa.Column("threshold", sa.Numeric(20, 8), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triggered_price", sa.Numeric(20, 8), nullable=True),
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_price_alerts_user_active",
        "price_alerts",
        ["user_id", "is_active"],
    )
    op.create_index(
        "ix_price_alerts_asset_active",
        "price_alerts",
        ["asset_type", "identifier", "is_active"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index("ix_price_alerts_asset_active", table_name="price_alerts")
    op.drop_index("ix_price_alerts_user_active", table_name="price_alerts")
    op.drop_table("price_alerts")
    op.drop_index("ix_watchlist_items_user_id", table_name="watchlist_items")
    op.drop_table("watchlist_items")

    postgresql.ENUM(name="alert_direction").drop(bind, checkfirst=True)
    postgresql.ENUM(name="asset_type").drop(bind, checkfirst=True)
