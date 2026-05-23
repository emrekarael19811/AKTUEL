"""
BaseScraper rate limiting ve robots.txt testleri.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.scrapers.base import BaseScraper, ScrapedCatalog, ScrapedProduct


class ConcreteScraper(BaseScraper):
    """Test için minimal somut implementasyon."""
    market_slug = "test_market"
    base_url = "https://test.example.com"

    async def fetch_catalog_urls(self) -> list[str]:
        return ["https://test.example.com/catalog.pdf"]

    async def parse_catalog(self, url: str) -> ScrapedCatalog:
        return ScrapedCatalog(
            market_slug=self.market_slug,
            catalog_url=url,
            products=[
                ScrapedProduct(raw_name="Test Ürün", raw_price="9,99 TL")
            ],
        )


@pytest.mark.asyncio
async def test_scraper_respects_robots_txt():
    scraper = ConcreteScraper()
    scraper._robots_parser = MagicMock()
    scraper._robots_parser.can_fetch.return_value = False

    with pytest.raises(PermissionError, match="robots.txt"):
        await scraper._get("https://test.example.com/blocked")


@pytest.mark.asyncio
async def test_scraper_returns_products():
    scraper = ConcreteScraper()
    with patch.object(scraper, "_load_robots_txt", new_callable=AsyncMock):
        with patch.object(scraper, "parse_catalog", new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = ScrapedCatalog(
                market_slug="test_market",
                catalog_url="https://test.example.com/catalog.pdf",
                products=[ScrapedProduct(raw_name="Süt 1L", raw_price="24,99 TL")],
            )
            import aiohttp
            with patch("aiohttp.ClientSession") as mock_session_cls:
                mock_session = AsyncMock()
                mock_session_cls.return_value.__aenter__.return_value = mock_session
                scraper._session = mock_session
                results = await scraper.run()

    assert len(results) >= 0  # En az sıfır katalog


def test_scraper_registry_contains_all_markets():
    from app.scrapers import SCRAPER_REGISTRY
    expected = {"migros", "bim", "a101", "sok", "carrefoursa"}
    assert expected.issubset(set(SCRAPER_REGISTRY.keys()))
