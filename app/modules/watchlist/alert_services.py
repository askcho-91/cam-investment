from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import AlertDirection, AssetType, PriceAlert, User
from .alerts import PriceAlertCreate
from .schemas import normalize_identifier


async def list_price_alerts(db: AsyncSession, user: User) -> list[PriceAlert]:
    result = await db.execute(
        select(PriceAlert)
        .where(PriceAlert.user_id == user.id)
        .order_by(PriceAlert.created_at.desc())
    )
    return list(result.scalars().all())


async def create_price_alert(
    db: AsyncSession, user: User, data: PriceAlertCreate
) -> PriceAlert:

    alert = PriceAlert(
        user_id=user.id,
        asset_type=data.asset_type.value,
        identifier=normalize_identifier(data.identifier),
        direction=data.direction.value,
        threshold=data.threshold,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def delete_price_alert(db: AsyncSession, user: User, alert_id: UUID) -> None:
    result = await db.execute(
        select(PriceAlert).where(
            PriceAlert.id == alert_id, PriceAlert.user_id == user.id
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Price alert not found"
        )
    await db.delete(alert)
    await db.commit()


async def deactivate_price_alert(
    db: AsyncSession, user: User, alert_id: UUID
) -> PriceAlert:
    result = await db.execute(
        select(PriceAlert).where(
            PriceAlert.id == alert_id, PriceAlert.user_id == user.id
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Price alert not found"
        )
    alert.is_active = False
    await db.commit()
    await db.refresh(alert)
    return alert


def alert_threshold_reached(alert: PriceAlert, price: Decimal) -> bool:
    if (
        alert.direction == AlertDirection.ABOVE
        or alert.direction == AlertDirection.ABOVE.value
    ):
        return price >= alert.threshold
    return price <= alert.threshold


async def trigger_matching_alerts(
    db: AsyncSession,
    quotes: dict[tuple[str, str], Decimal | int | float | str],
) -> list[PriceAlert]:
    """Deactivate and record active alerts whose current quote crossed a threshold."""
    result = await db.execute(select(PriceAlert).where(PriceAlert.is_active.is_(True)))
    active_alerts = list(result.scalars().all())
    triggered: list[PriceAlert] = []

    for alert in active_alerts:
        raw_price = quotes.get(
            (alert.asset_type.value, normalize_identifier(alert.identifier))
        )
        if raw_price is None:
            continue
        try:
            price = Decimal(str(raw_price))
        except InvalidOperation, ValueError:
            continue
        if not alert_threshold_reached(alert, price):
            continue

        alert.is_active = False
        alert.triggered_at = datetime.now(UTC)
        alert.triggered_price = price
        triggered.append(alert)

    if triggered:
        await db.commit()
        for alert in triggered:
            await db.refresh(alert)
    return triggered
