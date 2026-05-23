"""CarrefourSA haftalık indirim kataloğu scraper'ı."""

import logging
import re

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, ScrapedCatalog, ScrapedProduct
from app.ocr.pdf_extractor import extract_products_from_pdf

logger = logging.getLogger(__name__)


class CarrefoursaScraper(BaseScraper):
    market_slug = "carrefoursa"
    base_url = "https://www.carrefoursa.com"
    _catalog_url = "https://www.carrefoursa.com/kampanyalar/haftalik-indirim-katalogu"

    async def fetch_catalog_urls(self) -> list[str]:
        try:
            resp = await self._get(self._catalog_url)
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            urls = []
            for link in soup.select("a[href$='.pdf'], .catalog-download"):
                href = link.get("href", "")
                if href:
                    full_url = href if href.startswith("http") else self.base_url + href
                    urls.append(full_url)
            logger.info("[carrefoursa] %d katalog URL'si.", len(urls))
            return list(set(urls))
        except Exception as exc:
            logger.error("[carrefoursa] Hata: %s", exc, exc_info=True)
            return []

    async def parse_catalog(self, url: str) -> ScrapedCatalog:
        valid_from, valid_until = self._extract_dates_from_url(url)
        catalog = ScrapedCatalog(
            market_slug=self.market_slug,
            catalog_url=url,
            valid_from=valid_from,
            valid_until=valid_until,
            pdf_url=url if url.lower().endswith(".pdf") else None,
        )
        if url.lower().endswith(".pdf"):
            resp = await self._get(url)
            pdf_bytes = await resp.read()
            catalog.products = await extract_products_from_pdf(
                pdf_bytes, market_slug=self.market_slug
            )
        logger.info("[carrefoursa] Katalog: %d ürün", len(catalog.products))
        return catalog

    @staticmethod
    def _extract_dates_from_url(url: str) -> tuple[str | None, str | None]:
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", url)
        if len(dates) >= 2:
            return dates[0], dates[1]
        return (dates[0], None) if dates else (None, None)
