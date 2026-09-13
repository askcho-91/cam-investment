from sqlalchemy import Enum as SqlEnum, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .assets import AssetType
from .base_models import Base, BaseModel


class WatchlistItem(BaseModel, Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "asset_type", "identifier", name="uq_watchlist_user_asset"
        ),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_type: Mapped[AssetType] = mapped_column(
        SqlEnum(
            AssetType,
            name="asset_type",
            native_enum=True,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    identifier: Mapped[str] = mapped_column(Text, nullable=False)

    def __init__(self, *args, **kwargs):
        """Initializes the WatchlistItem instance."""
        super().__init__(*args, **kwargs)
