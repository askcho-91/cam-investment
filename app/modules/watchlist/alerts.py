from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.models import AlertDirection, AssetType
from .schemas import normalize_identifier


class PriceAlertCreate(BaseModel):
    asset_type: AssetType = AssetType.GLOBAL_STOCK
    identifier: str = Field(min_length=1, max_length=100)
    direction: AlertDirection
    threshold: Decimal = Field(gt=0, max_digits=20, decimal_places=8)

    @field_validator("identifier")
    @classmethod
    def clean_identifier(cls, value: str) -> str:
        return normalize_identifier(value)


class PriceAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_type: AssetType
    identifier: str
    direction: AlertDirection
    threshold: Decimal
    is_active: bool
    triggered_at: datetime | None
    triggered_price: Decimal | None
    created_at: datetime
    updated_at: datetime