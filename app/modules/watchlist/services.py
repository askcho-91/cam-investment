from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import User, WatchlistItem
from .schemas import WatchlistItemCreate, normalize_identifier


async def list_watchlist(db: AsyncSession, user: User) -> list[WatchlistItem]:
    result = await db.execute(
        select(WatchlistItem)
        .where(WatchlistItem.user_id == user.id)
        .order_by(WatchlistItem.created_at.desc())
    )
    return list(result.scalars().all())


async def get_watchlist_item(db: AsyncSession, user: User, asset_type: str, identifier: str) -> WatchlistItem:
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user.id,
            WatchlistItem.asset_type == asset_type,
            WatchlistItem.identifier == normalize_identifier(identifier),
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist item not found")
    return item


async def create_watchlist_item(db: AsyncSession, user: User, data: WatchlistItemCreate) -> WatchlistItem:
    item = WatchlistItem(user_id=user.id, asset_type=data.asset_type, identifier=data.identifier)
    db.add(item)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Asset is already on the watchlist") from exc
    await db.refresh(item)
    return item


async def delete_watchlist_item(db: AsyncSession, user: User, asset_type: str, identifier: str) -> None:
    item = await get_watchlist_item(db, user, asset_type, identifier)
    await db.delete(item)
    await db.commit()