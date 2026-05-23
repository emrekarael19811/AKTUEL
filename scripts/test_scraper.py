"""
Scraper test scripti - Supabase'e kayit eder.
Kullanim: python scripts/test_scraper.py [market_slug]
Ornek:    python scripts/test_scraper.py bim
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# backend/ dizinini path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
os.chdir(Path(__file__).parent.parent / "backend")

# .env yukle
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


async def test_scraper(market_slug: str):
    from app.scrapers import SCRAPER_REGISTRY
    from app.utils.turkish import parse_price_tl, parse_unit, compute_unit_price

    if market_slug not in SCRAPER_REGISTRY:
        print(f"Bilinen marketler: {', '.join(SCRAPER_REGISTRY.keys())}")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"  {market_slug.upper()} Scraper Testi")
    print(f"{'='*50}\n")

    scraper_class = SCRAPER_REGISTRY[market_slug]
    scraper = scraper_class()

    print(f"[1] Katalog URL'leri aliniyor...")
    try:
        import aiohttp
        async with aiohttp.ClientSession(
            headers={"User-Agent": "AKTUEL-Bot/1.0 (+https://aktuel.app/bot)"},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as session:
            scraper._session = session
            await scraper._load_robots_txt()
            urls = await scraper.fetch_catalog_urls()

        print(f"  ✓ {len(urls)} URL bulundu")
        for u in urls[:3]:
            print(f"    → {u}")
        if len(urls) > 3:
            print(f"    ... ve {len(urls)-3} tane daha")

    except Exception as e:
        print(f"  ✗ Hata: {e}")
        print("\n  [Sahte veri ile devam ediliyor - offline test modu]")
        urls = []

    # Sahte urun testi (network olmasa bile calisir)
    print(f"\n[2] Fiyat parse testi:")
    test_prices = ["14,99 TL", "₺29,90", "1.499,00 TL", "900,0", "0,00"]
    for raw in test_prices:
        result = parse_price_tl(raw)
        status = "✓" if result else "✗ (None)"
        print(f"  {status} '{raw}' → {result}")

    print(f"\n[3] Birim parse testi:")
    test_units = ["500 gr", "1 kg", "1,5 lt", "330 ml", "6 adet"]
    for raw in test_units:
        unit_type, qty = parse_unit(raw)
        unit_price = compute_unit_price(10.0, unit_type, qty) if unit_type else None
        print(f"  ✓ '{raw}' → ({unit_type}, {qty}) | 10TL için birim fiyat: {unit_price}")

    # Supabase baglanti testi
    print(f"\n[4] Supabase baglanti testi:")
    try:
        import asyncpg
        db_url = os.environ.get("DATABASE_URL", "")
        if not db_url:
            print("  ✗ DATABASE_URL tanimli degil")
        else:
            # asyncpg icin URL'yi parse et
            if "pooler.supabase.com" in db_url:
                # Pooler formatini kullan
                conn = await asyncpg.connect(db_url + "?sslmode=require")
            else:
                conn = await asyncpg.connect(db_url, ssl="require")

            markets = await conn.fetch("SELECT name, slug FROM markets ORDER BY id")
            print(f"  ✓ Supabase baglantisi basarili! {len(markets)} market:")
            for m in markets:
                print(f"    → {m['name']} ({m['slug']})")
            await conn.close()
    except Exception as e:
        print(f"  ✗ Baglanti hatasi: {e}")
        print("  → DATABASE_URL'yi kontrol edin (.env dosyasi)")

    print(f"\n{'='*50}")
    print(f"  Test tamamlandi!")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else "bim"
    asyncio.run(test_scraper(slug))
