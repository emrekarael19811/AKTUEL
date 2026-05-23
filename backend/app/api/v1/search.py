from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from app.search import search_client

router = APIRouter(prefix="/search", tags=["search"])


class ProductSearchResult(BaseModel):
    product_id: int
    name: str
    market_name: str
    market_slug: str
    price_tl: Optional[float]
    original_price_tl: Optional[float]
    discount_pct: Optional[float]
    unit_price_tl: Optional[float]
    unit_type: Optional[str]
    unit_size: Optional[float]
    image_url: Optional[str]
    valid_from: Optional[str]
    valid_until: Optional[str]
    highlight: Optional[dict] = None


class SearchResponse(BaseModel):
    total: int
    products: list[ProductSearchResult]
    query: str


@router.get("/", response_model=SearchResponse)
async def search_products(
    q: str = Query(..., min_length=2, max_length=200, description="Arama sorgusu"),
    markets: Optional[str] = Query(None, description="Virgülle ayrılmış market slug'ları: bim,a101"),
    category: Optional[str] = None,
    max_price: Optional[float] = Query(None, ge=0),
    min_discount: Optional[float] = Query(None, ge=0, le=100),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """
    Türkçe fuzzy ürün arama.
    Sonuçlar birim fiyat (unit_price_tl) bazında ucuzdan pahalıya sıralanır.
    """
    market_slugs = [m.strip() for m in markets.split(",")] if markets else None
    from_ = (page - 1) * size

    try:
        result = await search_client.search(
            query=q,
            market_slugs=market_slugs,
            category=category,
            max_price_tl=max_price,
            min_discount_pct=min_discount,
            from_=from_,
            size=size,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Arama servisi hatası: {exc}")

    return SearchResponse(
        total=result["total"],
        products=result["products"],
        query=q,
    )


@router.get("/suggest")
async def suggest_products(
    q: str = Query(..., min_length=1, max_length=100),
    size: int = Query(5, ge=1, le=10),
) -> list[str]:
    """Arama otomatik tamamlama."""
    try:
        return await search_client.suggest(prefix=q, size=size)
    except Exception:
        return []
