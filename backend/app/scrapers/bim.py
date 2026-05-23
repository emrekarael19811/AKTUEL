"""
BİM haftalık aktüel ürünler scraper'ı.
BİM her Cuma yeni ürün sayfası yayınlar.
Prophet ile tahmin edilen yayın tarihleri göz önüne alınarak erken kontrol yapılır.
"""

import logging
import re

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, ScrapedCatalog, ScrapedProduct
from app.ocr.pdf_extractor import extract_products_from_pdf

logger = logging.getLogger(__name__)

# BİM her Cuma (weekday=4) yayın yapar
BIM_PUBLISH_WEEKDAY = 4


class BimScraper(BaseScraper):
    market_slug = "bim"
    base_url = "https://www.bim.com.tr"
    _aktuel_url = "https://www.bim.com.tr/Modules/ActuelProducts/ActuelProducts.aspx"

    async def fetch_catalog_urls(self) -> list[str]:
        try:
            resp = await self._get(self._aktuel_url)
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")

            urls = []
            for link in soup.select("a.BrochureBoxButton, a[href$='.pdf']"):
                href = link.get("href", "")
                if href:
                    full_url = href if href.startswith("http") else self.base_url + href
                    urls.append(full_url)

            # Broşür sayfası ayrı bir endpoint olabilir
            for anchor in soup.find_all("a", href=re.compile(r"aktuel|aktuell|brosur", re.I)):
                href = anchor.get("href", "")
                if href and href not in urls:
                    full_url = href if href.startswith("http") else self.base_url + href
                    urls.append(full_url)

            logger.info("[bim] %d katalog URL'si bulundu.", len(urls))
            return list(set(urls))

        except Exception as exc:
            logger.error("[bim] fetch_catalog_urls hatası: %s", exc, exc_info=True)
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

        logger.info(
            "[bim] Katalog parse edildi: %d ürün, URL: %s",
            len(catalog.products), url
        )
        return catalog

    def _parse_html_products(self, html: str) -> list[ScrapedProduct]:
        soup = BeautifulSoup(html, "html.parser")
        products = []
        for item in soup.select(".product-item, .ActuelProductItem, li.product"):
            name_el = item.select_one(
                ".product-title, .ActuelProductTitle, h2, h3, h4"
            )
            price_el = item.select_one(".price, .ActuelProductPrice, .product-price")
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
