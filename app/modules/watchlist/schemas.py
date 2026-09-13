from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.models import AssetType


def normalize_identifier(value: str) -> str:
    return value.strip().upper()


class WatchlistItemCreate(BaseModel):
    asset_type: AssetType = AssetType.GLOBAL_STOCK
    identifier: str = Field(min_length=1, max_length=100)

    @field_validator("identifier")
    @classmethod
    def clean_identifier(cls, value: str) -> str:
        return normalize_identifier(value)


class WatchlistItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_type: AssetType
    identifier: str
    created_at: datetime
    updated_at: datetime