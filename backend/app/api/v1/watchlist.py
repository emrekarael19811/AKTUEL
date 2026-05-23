from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Watchlist, CanonicalProduct

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class WatchlistCreate(BaseModel):
    canonical_product_id: int
    price_threshold_tl: Optional[float] = Field(None, gt=0)
    unit_price_threshold_tl: Optional[float] = Field(None, gt=0)
    notify_on_any_discount: bool = True
    notify_early: bool = True


class WatchlistResponse(BaseModel):
    id: int
    canonical_product_id: int
    price_threshold_tl: Optional[float]
    unit_price_threshold_tl: Optional[float]
    notify_on_any_discount: bool
    notify_early: bool
    is_active: bool

    model_config = {"from_attributes": True}


def get_current_user_id() -> str:
    # Supabase JWT token doğrulaması burada yapılır.
    # Production'da: from app.auth import verify_jwt_token
    return "placeholder-user-id"


@router.get("/", response_model=list[WatchlistResponse])
async def get_watchlist(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Watchlist)
        .where(Watchlist.user_id == user_id, Watchlist.is_active == True)
        .order_by(Watchlist.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    payload: WatchlistCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    # Ürün var mı kontrol et
    prod = await db.get(CanonicalProduct, payload.canonical_product_id)
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ürün bulunamadı.",
        )

    # Aynı ürün zaten takipte mi?
    existing = await db.execute(
        select(Watchlist).where(
            Watchlist.user_id == user_id,
            Watchlist.canonical_product_id == payload.canonical_product_id,
            Watchlist.is_active == True,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu ürün zaten takip listenizde.",
        )

    item = Watchlist(
        user_id=user_id,
        canonical_product_id=payload.canonical_product_id,
        price_threshold_tl=payload.price_threshold_tl,
        unit_price_threshold_tl=payload.unit_price_threshold_tl,
        notify_on_any_discount=payload.notify_on_any_discount,
        notify_early=payload.notify_early,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(
    item_id: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Watchlist).where(
            Watchlist.id == item_id, Watchlist.user_id == user_id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kayıt bulunamadı.")
    item.is_active = False
    await db.commit()
