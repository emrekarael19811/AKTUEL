from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import RawProduct, ProductPrice, Market, Catalog

router = APIRouter(prefix="/products", tags=["products"])


class ProductResponse(BaseModel):
    id: int
    raw_name: str
    raw_price: Optional[str]
    raw_unit: Optional[str]
    image_url: Optional[str]
    market_name: str
    market_slug: str
    price_tl: Optional[float]
    discount_pct: Optional[float]
    unit_price_tl: Optional[float]
    valid_from: Optional[date]
    valid_until: Optional[date]

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[ProductResponse])
async def list_products(
    market_slug: Optional[str] = None,
    catalog_id: Optional[int] = None,
    active_only: bool = True,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Ürünleri listele. unit_price_tl bazında ucuzdan pahalıya sıralı.
    """
    query = (
        select(RawProduct, ProductPrice, Market)
        .join(ProductPrice, RawProduct.id == ProductPrice.raw_product_id)
        .join(Market, ProductPrice.market_id == Market.id)
    )

    filters = []
    if market_slug:
        filters.append(Market.slug == market_slug)
    if catalog_id:
        filters.append(RawProduct.catalog_id == catalog_id)
    if active_only:
        today = date.today()
        filters.append(ProductPrice.valid_from <= today)
        filters.append(ProductPrice.valid_until >= today)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(ProductPrice.unit_price_tl.asc().nullslast())
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    rows = result.all()

    return [
        ProductResponse(
            id=raw.id,
            raw_name=raw.raw_name,
            raw_price=raw.raw_price,
            raw_unit=raw.raw_unit,
            image_url=raw.image_url,
            market_name=market.name,
            market_slug=market.slug,
            price_tl=price.price_tl,
            discount_pct=price.discount_pct,
            unit_price_tl=price.unit_price_tl,
            valid_from=price.valid_from,
            valid_until=price.valid_until,
        )
        for raw, price, market in rows
    ]


@router.get("/{product_id}/price-history")
async def get_price_history(
    product_id: int,
    days: int = Query(90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Bir ürünün fiyat tarihçesini döndür."""
    from datetime import timedelta
    from sqlalchemy import func

    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(
            ProductPrice.valid_from,
            ProductPrice.price_tl,
            ProductPrice.unit_price_tl,
            Market.name.label("market_name"),
            Market.slug.label("market_slug"),
        )
        .join(Market, ProductPrice.market_id == Market.id)
        .join(RawProduct, ProductPrice.raw_product_id == RawProduct.id)
        .where(
            RawProduct.canonical_product_id == product_id,
            ProductPrice.valid_from >= since,
        )
        .order_by(ProductPrice.valid_from.asc())
    )
    rows = result.all()
    return [
        {
            "date": r.valid_from.isoformat(),
            "price_tl": r.price_tl,
            "unit_price_tl": r.unit_price_tl,
            "market": r.market_name,
            "market_slug": r.market_slug,
        }
        for r in rows
    ]
