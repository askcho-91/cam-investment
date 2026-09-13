from typing import Annotated

from fastapi import APIRouter, Path, status

from app.core.dependencies import (
    current_user_dependency,
    db_dependency,
    authorization_header,
)
from app.core.models import AssetType
from .schemas import WatchlistItemCreate, WatchlistItemResponse
from .services import (
    create_watchlist_item,
    delete_watchlist_item,
    get_watchlist_item,
    list_watchlist,
)

watchlist_router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


@watchlist_router.get("", response_model=list[WatchlistItemResponse])
async def get_watchlist(
    db: db_dependency, user: current_user_dependency, auth: authorization_header
):
    return await list_watchlist(db, user)


@watchlist_router.post(
    "", response_model=WatchlistItemResponse, status_code=status.HTTP_201_CREATED
)
async def add_watchlist_item(
    data: WatchlistItemCreate, db: db_dependency, user: current_user_dependency, auth: authorization_header
):
    return await create_watchlist_item(db, user, data)


@watchlist_router.get(
    "/{asset_type}/{identifier:path}", response_model=WatchlistItemResponse
)
async def get_one_watchlist_item(
    asset_type: AssetType,
    identifier: Annotated[str, Path(min_length=1, max_length=100)],
    db: db_dependency,
    user: current_user_dependency,
    auth: authorization_header,
):
    return await get_watchlist_item(db, user, asset_type, identifier)


@watchlist_router.delete(
    "/{asset_type}/{identifier:path}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_watchlist_item(
    asset_type: AssetType,
    identifier: Annotated[str, Path(min_length=1, max_length=100)],
    db: db_dependency,
    user: current_user_dependency,
    auth: authorization_header,
):
    await delete_watchlist_item(db, user, asset_type, identifier)
