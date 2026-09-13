from uuid import UUID

from fastapi import APIRouter, status

from app.core.dependencies import (
    current_user_dependency,
    db_dependency,
    authorization_header,
)
from .alert_services import (
    create_price_alert,
    deactivate_price_alert,
    delete_price_alert,
    list_price_alerts,
)
from .alerts import PriceAlertCreate, PriceAlertResponse

price_alert_router = APIRouter(prefix="/price-alerts", tags=["Price alerts"])


@price_alert_router.get("", response_model=list[PriceAlertResponse])
async def get_price_alerts(
    db: db_dependency, user: current_user_dependency, auth: authorization_header
):
    return await list_price_alerts(db, user)


@price_alert_router.post(
    "", response_model=PriceAlertResponse, status_code=status.HTTP_201_CREATED
)
async def add_price_alert(
    data: PriceAlertCreate,
    db: db_dependency,
    user: current_user_dependency,
    auth: authorization_header,
):
    return await create_price_alert(db, user, data)


@price_alert_router.patch("/{alert_id}/deactivate", response_model=PriceAlertResponse)
async def deactivate_alert(
    alert_id: UUID,
    db: db_dependency,
    user: current_user_dependency,
    auth: authorization_header,
):
    return await deactivate_price_alert(db, user, alert_id)


@price_alert_router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_price_alert(
    alert_id: UUID,
    db: db_dependency,
    user: current_user_dependency,
    auth: authorization_header,
):
    await delete_price_alert(db, user, alert_id)
