from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from .assets import AlertDirection, AssetType
from .base_models import Base, BaseModel


class PriceAlert(BaseModel, Base):
    __tablename__ = "price_alerts"

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
    identifier: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    direction: Mapped[AlertDirection] = mapped_column(
        SqlEnum(
            AlertDirection,
            name="alert_direction",
            native_enum=True,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    threshold: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )
    triggered_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    triggered_price: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )

    def __init__(self, *args, **kwargs):
        """Initializes the PriceAlert instance."""
        super().__init__(*args, **kwargs)
