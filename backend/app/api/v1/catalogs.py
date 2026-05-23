from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Catalog, Market
from app.models.catalog import CatalogStatus

router = APIRouter(prefix="/catalogs", tags=["catalogs"])


class CatalogResponse(BaseModel):
    id: int
    market_id: int
    market_name: str
    market_slug: str
    valid_from: Optional[date]
    valid_until: Optional[date]
    pdf_url: Optional[str]
    status: CatalogStatus
    raw_product_count: int

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[CatalogResponse])
async def list_catalogs(
    market_slug: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Aktif katalogları listele."""
    query = (
        select(Catalog, Market.name, Market.slug)
        .join(Market, Catalog.market_id == Market.id)
    )
    if market_slug:
        query = query.where(Market.slug == market_slug)
    if active_only:
        today = date.today()
        query = query.where(
            Catalog.valid_from <= today,
            Catalog.valid_until >= today,
            Catalog.status == CatalogStatus.ACTIVE,
        )
    result = await db.execute(query.order_by(Catalog.valid_from.desc()))
    rows = result.all()

    return [
        CatalogResponse(
            id=cat.id,
            market_id=cat.market_id,
            market_name=market_name,
            market_slug=market_slug_val,
            valid_from=cat.valid_from,
            valid_until=cat.valid_until,
            pdf_url=cat.pdf_url,
            status=cat.status,
            raw_product_count=cat.raw_product_count or 0,
        )
        for cat, market_name, market_slug_val in rows
    ]


@router.get("/{catalog_id}", response_model=CatalogResponse)
async def get_catalog(catalog_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Catalog, Market.name, Market.slug)
        .join(Market, Catalog.market_id == Market.id)
        .where(Catalog.id == catalog_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Katalog bulunamadı.")
    cat, market_name, market_slug_val = row
    return CatalogResponse(
        id=cat.id,
        market_id=cat.market_id,
        market_name=market_name,
        market_slug=market_slug_val,
        valid_from=cat.valid_from,
        valid_until=cat.valid_until,
        pdf_url=cat.pdf_url,
        status=cat.status,
        raw_product_count=cat.raw_product_count or 0,
    )
