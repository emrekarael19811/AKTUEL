"""
Veritabanına başlangıç market verilerini ekler.
Çalıştırma: python scripts/seed_markets.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import AsyncSessionLocal, engine, Base
from app.models.market import Market, ScraperType


MARKETS = [
    {
        "name": "BİM",
        "slug": "bim",
        "website_url": "https://www.bim.com.tr",
        "catalog_url": "https://www.bim.com.tr/Modules/ActuelProducts/ActuelProducts.aspx",
        "logo_url": None,
        "scraper_type": ScraperType.WEB,
        "catalog_cycle_days": 7,
        "catalog_publish_weekday": 4,  # Cuma
        "is_active": True,
    },
    {
        "name": "A101",
        "slug": "a101",
        "website_url": "https://www.a101.com.tr",
        "catalog_url": "https://www.a101.com.tr/a101-aktuel-urunler",
        "logo_url": None,
        "scraper_type": ScraperType.WEB,
        "catalog_cycle_days": 7,
        "catalog_publish_weekday": 3,  # Perşembe
        "is_active": True,
    },
    {
        "name": "Migros",
        "slug": "migros",
        "website_url": "https://www.migros.com.tr",
        "catalog_url": "https://www.migros.com.tr/kampanyalar/kataloglar",
        "logo_url": None,
        "scraper_type": ScraperType.PDF,
        "catalog_cycle_days": 7,
        "catalog_publish_weekday": 4,  # Cuma
        "is_active": True,
    },
    {
        "name": "ŞOK Market",
        "slug": "sok",
        "website_url": "https://www.sokmarket.com.tr",
        "catalog_url": "https://www.sokmarket.com.tr/aktuel-urunler",
        "logo_url": None,
        "scraper_type": ScraperType.WEB,
        "catalog_cycle_days": 7,
        "catalog_publish_weekday": 3,  # Perşembe
        "is_active": True,
    },
    {
        "name": "CarrefourSA",
        "slug": "carrefoursa",
        "website_url": "https://www.carrefoursa.com",
        "catalog_url": "https://www.carrefoursa.com/kampanyalar/haftalik-indirim-katalogu",
        "logo_url": None,
        "scraper_type": ScraperType.PDF,
        "catalog_cycle_days": 7,
        "catalog_publish_weekday": 3,  # Perşembe
        "is_active": True,
    },
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Tablolar oluşturuldu/doğrulandı.")

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        for market_data in MARKETS:
            existing = await db.execute(
                select(Market).where(Market.slug == market_data["slug"])
            )
            if existing.scalar_one_or_none():
                print(f"[SKIP] {market_data['name']} zaten mevcut.")
                continue

            market = Market(**market_data)
            db.add(market)
            print(f"[ADD] {market_data['name']} eklendi.")

        await db.commit()
        print("Seed tamamlandı.")


if __name__ == "__main__":
    asyncio.run(seed())
