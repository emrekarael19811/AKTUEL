"""
Celery görevleri: Scraping, OCR, ürün eşleştirme ve indeksleme pipeline'ı.
"""

import logging
from datetime import date

from celery import shared_task

from app.scrapers import SCRAPER_REGISTRY, ScrapedProduct
from app.utils.turkish import parse_price_tl, parse_unit, compute_unit_price

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 dakika
    name="tasks.scrape_market",
)
def scrape_market(self, market_slug: str) -> dict:
    """
    Tek bir market için scraping + DB kayıt görevini çalıştır.
    Async scraper'ı sync Celery görevinde asyncio.run ile wrap eder.
    """
    import asyncio

    try:
        result = asyncio.run(_async_scrape_market(market_slug))
        return result
    except Exception as exc:
        logger.error("[%s] Scraping görevi başarısız: %s", market_slug, exc, exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    name="tasks.scrape_all_markets",
)
def scrape_all_markets(self) -> dict:
    """Tüm aktif marketleri sırayla scrape et (Celery Beat tarafından tetiklenir)."""
    results = {}
    for slug in SCRAPER_REGISTRY:
        task = scrape_market.delay(slug)
        results[slug] = task.id
        logger.info("[scheduler] %s scraping görevi kuyruğa alındı: %s", slug, task.id)
    return results


@shared_task(name="tasks.index_catalog_products")
def index_catalog_products(catalog_id: int) -> dict:
    """Belirli bir kataloğun ürünlerini Elasticsearch'e indeksle."""
    import asyncio
    return asyncio.run(_async_index_catalog(catalog_id))


async def _async_scrape_market(market_slug: str) -> dict:
    """Async scraping + DB persist pipeline."""
    scraper_class = SCRAPER_REGISTRY.get(market_slug)
    if not scraper_class:
        raise ValueError(f"Bilinmeyen market slug: {market_slug}")

    scraper = scraper_class()
    catalogs = await scraper.run()

    total_products = 0
    for catalog in catalogs:
        saved = await _persist_catalog(market_slug, catalog)
        total_products += saved

    logger.info("[%s] Toplam %d ürün kaydedildi.", market_slug, total_products)
    return {"market": market_slug, "catalogs": len(catalogs), "products": total_products}


async def _persist_catalog(market_slug: str, catalog) -> int:
    """ScrapedCatalog'u veritabanına kaydet."""
    from app.database import AsyncSessionLocal
    from app.models import Market, Catalog, RawProduct, ProductPrice
    from app.models.catalog import CatalogStatus
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        try:
            # Market'i bul
            result = await db.execute(
                select(Market).where(Market.slug == market_slug)
            )
            market = result.scalar_one_or_none()
            if not market:
                logger.error("Market bulunamadı: %s", market_slug)
                return 0

            # Katalog oluştur
            db_catalog = Catalog(
                market_id=market.id,
                valid_from=_parse_date(catalog.valid_from),
                valid_until=_parse_date(catalog.valid_until),
                pdf_url=catalog.pdf_url,
                catalog_url=catalog.catalog_url,
                status=CatalogStatus.PARSING,
                raw_product_count=len(catalog.products),
            )
            db.add(db_catalog)
            await db.flush()  # ID al

            saved = 0
            for product in catalog.products:
                raw = await _persist_product(db, db_catalog.id, market.id, product)
                if raw:
                    saved += 1

            db_catalog.status = CatalogStatus.ACTIVE
            db_catalog.raw_product_count = saved
            await db.commit()
            return saved

        except Exception as exc:
            await db.rollback()
            logger.error("Katalog kaydetme hatası: %s", exc, exc_info=True)
            return 0


async def _persist_product(db, catalog_id: int, market_id: int, product: ScrapedProduct):
    """Tek bir ScrapedProduct'ı DB'ye kaydet + fiyat hesapla."""
    from app.models import RawProduct, ProductPrice

    price_tl = parse_price_tl(product.raw_price) if product.raw_price else None
    unit_type, unit_size = parse_unit(product.raw_unit) if product.raw_unit else (None, None)
    unit_price = compute_unit_price(price_tl, unit_type, unit_size) if price_tl else None

    raw = RawProduct(
        catalog_id=catalog_id,
        raw_name=product.raw_name,
        raw_price=product.raw_price,
        raw_unit=product.raw_unit,
        raw_discount_text=product.raw_discount_text,
        image_url=product.image_url,
        page_number=product.page_number,
    )
    db.add(raw)
    await db.flush()

    if price_tl:
        pp = ProductPrice(
            raw_product_id=raw.id,
            market_id=market_id,
            catalog_id=catalog_id,
            price_tl=price_tl,
            unit_price_tl=unit_price,
            valid_from=date.today(),
            valid_until=date.today(),
        )
        db.add(pp)

    return raw


async def _async_index_catalog(catalog_id: int) -> dict:
    from app.database import AsyncSessionLocal
    from app.models import RawProduct, ProductPrice, Market
    from app.search import search_client
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(RawProduct, ProductPrice, Market)
            .join(ProductPrice, RawProduct.id == ProductPrice.raw_product_id)
            .join(Market, ProductPrice.market_id == Market.id)
            .where(RawProduct.catalog_id == catalog_id)
        )
        rows = result.all()

    products = []
    for raw, price, market in rows:
        products.append({
            "product_id": raw.id,
            "market_id": market.id,
            "market_name": market.name,
            "market_slug": market.slug,
            "name": raw.raw_name,
            "price_tl": price.price_tl,
            "discount_pct": price.discount_pct,
            "unit_price_tl": price.unit_price_tl,
            "valid_from": price.valid_from.isoformat() if price.valid_from else None,
            "valid_until": price.valid_until.isoformat() if price.valid_until else None,
            "is_active": True,
            "image_url": raw.image_url,
        })

    indexed = await search_client.index_products(products)
    return {"catalog_id": catalog_id, "indexed": indexed}


def _parse_date(date_str):
    if not date_str:
        return None
    try:
        from datetime import datetime
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
