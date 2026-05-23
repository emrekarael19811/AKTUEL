"""
Migros haftalık indirim kataloğu scraper'ı.
Migros kataloglarını web sitesi üzerinden PDF formatında çeker.
"""

import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, ScrapedCatalog, ScrapedProduct
from app.ocr.pdf_extractor import extract_products_from_pdf

logger = logging.getLogger(__name__)


class MigrosScraper(BaseScraper):
    market_slug = "migros"
    base_url = "https://www.migros.com.tr"
    _catalog_list_url = "https://www.migros.com.tr/kampanyalar/kataloglar"

    async def fetch_catalog_urls(self) -> list[str]:
        try:
            resp = await self._get(self._catalog_list_url)
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")

            urls = []
            # Migros katalog kartlarını bul
            for link in soup.select("a[href*='katalog'], a[href*='brosur']"):
                href = link.get("href", "")
                if href and "pdf" in href.lower():
                    full_url = href if href.startswith("http") else self.base_url + href
                    urls.append(full_url)

            # PDF olmayan katalog sayfaları için alt sayfa kontrolü
            for card in soup.select(".catalog-card, .brochure-card"):
                link = card.find("a")
                if link:
                    sub_url = link.get("href", "")
                    if sub_url and not sub_url.startswith("http"):
                        sub_url = self.base_url + sub_url
                    pdf_url = await self._find_pdf_in_page(sub_url)
                    if pdf_url:
                        urls.append(pdf_url)

            logger.info("[migros] %d katalog URL'si bulundu.", len(urls))
            return list(set(urls))

        except Exception as exc:
            logger.error("[migros] fetch_catalog_urls hatası: %s", exc, exc_info=True)
            return []

    async def parse_catalog(self, url: str) -> ScrapedCatalog:
        # Geçerlilik tarihlerini URL veya sayfa metninden çıkarmayı dene
        valid_from, valid_until = self._extract_dates_from_url(url)

        catalog = ScrapedCatalog(
            market_slug=self.market_slug,
            catalog_url=url,
            valid_from=valid_from,
            valid_until=valid_until,
            pdf_url=url if url.endswith(".pdf") else None,
        )

        if url.endswith(".pdf"):
            # PDF'den OCR ile ürün çıkar
            resp = await self._get(url)
            pdf_bytes = await resp.read()
            products = await extract_products_from_pdf(pdf_bytes, market_slug=self.market_slug)
            catalog.products = products
        else:
            # HTML sayfa ise ürünleri HTML'den parse et
            resp = await self._get(url)
            html = await resp.text()
            catalog.products = self._parse_html_products(html)

        logger.info(
            "[migros] Katalog parse edildi: %d ürün, URL: %s",
            len(catalog.products), url
        )
        return catalog

    async def _find_pdf_in_page(self, page_url: str) -> str | None:
        try:
            resp = await self._get(page_url)
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.find_all("a", href=True):
                if ".pdf" in link["href"].lower():
                    href = link["href"]
                    return href if href.startswith("http") else self.base_url + href
        except Exception as exc:
            logger.warning("[migros] PDF link bulunamadı %s: %s", page_url, exc)
        return None

    def _parse_html_products(self, html: str) -> list[ScrapedProduct]:
        soup = BeautifulSoup(html, "html.parser")
        products = []
        for item in soup.select(".product-card, .campaign-product"):
            name_el = item.select_one(".product-name, h3, h4")
            price_el = item.select_one(".price, .campaign-price")
            unit_el = item.select_one(".unit, .weight")
            img_el = item.select_one("img")

            if not name_el:
                continue

            products.append(ScrapedProduct(
                raw_name=name_el.get_text(strip=True),
                raw_price=price_el.get_text(strip=True) if price_el else None,
                raw_unit=unit_el.get_text(strip=True) if unit_el else None,
                image_url=img_el.get("src") if img_el else None,
            ))
        return products

    @staticmethod
    def _extract_dates_from_url(url: str) -> tuple[str | None, str | None]:
        # "2025-05-24" formatını URL'den çıkar
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", url)
        if len(dates) >= 2:
            return dates[0], dates[1]
        if len(dates) == 1:
            return dates[0], None
        return None, None
