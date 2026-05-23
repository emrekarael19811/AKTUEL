from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Market

router = APIRouter(prefix="/markets", tags=["markets"])


class MarketResponse(BaseModel):
    id: int
    name: str
    slug: str
    website_url: str
    logo_url: Optional[str]
    catalog_cycle_days: int
    catalog_publish_weekday: Optional[int]
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[MarketResponse])
async def list_markets(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Tüm marketleri listele."""
    query = select(Market)
    if active_only:
        query = query.where(Market.is_active == True)
    result = await db.execute(query.order_by(Market.name))
    return result.scalars().all()


@router.get("/{slug}", response_model=MarketResponse)
async def get_market(slug: str, db: AsyncSession = Depends(get_db)):
    """Tek bir marketi slug ile getir."""
    result = await db.execute(select(Market).where(Market.slug == slug))
    market = result.scalar_one_or_none()
    if not market:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market bulunamadı.")
    return market
