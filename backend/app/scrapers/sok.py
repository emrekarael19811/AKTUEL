"""ŞOK Market haftalık aktüel ürünler scraper'ı."""

import logging
import re

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, ScrapedCatalog, ScrapedProduct
from app.ocr.pdf_extractor import extract_products_from_pdf

logger = logging.getLogger(__name__)


class SokScraper(BaseScraper):
    market_slug = "sok"
    base_url = "https://www.sokmarket.com.tr"
    _aktuel_url = "https://www.sokmarket.com.tr/aktuel-urunler"

    async def fetch_catalog_urls(self) -> list[str]:
        try:
            resp = await self._get(self._aktuel_url)
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            urls = []
            for link in soup.select("a[href$='.pdf'], a[href*='katalog'], a[href*='brosur']"):
                href = link.get("href", "")
                if href:
                    full_url = href if href.startswith("http") else self.base_url + href
                    urls.append(full_url)
            logger.info("[sok] %d katalog URL'si bulundu.", len(urls))
            return list(set(urls))
        except Exception as exc:
            logger.error("[sok] fetch_catalog_urls hatası: %s", exc, exc_info=True)
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
        else:
            resp = await self._get(url)
            html = await resp.text()
            catalog.products = self._parse_html_products(html)
        logger.info("[sok] Katalog: %d ürün", len(catalog.products))
        return catalog

    def _parse_html_products(self, html: str) -> list[ScrapedProduct]:
        soup = BeautifulSoup(html, "html.parser")
        products = []
        for item in soup.select(".product, .aktuel-item, .urun"):
            name_el = item.select_one(".name, h3, h4, .title")
            price_el = item.select_one(".price, .fiyat")
            img_el = item.select_one("img")
            if not name_el:
                continue
            products.append(ScrapedProduct(
                raw_name=name_el.get_text(strip=True),
                raw_price=price_el.get_text(strip=True) if price_el else None,
                image_url=img_el.get("src") if img_el else None,
            ))
        return products

    @staticmethod
    def _extract_dates_from_url(url: str) -> tuple[str | None, str | None]:
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", url)
        if len(dates) >= 2:
            return dates[0], dates[1]
        if len(dates) == 1:
            return dates[0], None
        return None, None
