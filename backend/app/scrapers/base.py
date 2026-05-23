"""
Tüm market scraper'larının miras aldığı soyut temel sınıf.
robots.txt kontrolü, rate limiting ve hata yönetimi burada merkezileştirilmiştir.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import aiohttp

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ScrapedProduct:
    raw_name: str
    raw_price: Optional[str] = None
    raw_unit: Optional[str] = None
    raw_discount_text: Optional[str] = None
    image_url: Optional[str] = None
    page_number: Optional[int] = None
    extra: dict = field(default_factory=dict)


@dataclass
class ScrapedCatalog:
    market_slug: str
    catalog_url: str
    valid_from: Optional[str] = None   # ISO date: "2025-05-24"
    valid_until: Optional[str] = None
    pdf_url: Optional[str] = None
    products: list[ScrapedProduct] = field(default_factory=list)


class BaseScraper(ABC):
    """
    Tüm scraper'ların uyması gereken kontrat.

    Alt sınıflar yalnızca `fetch_catalog_urls()` ve `parse_catalog()` metodlarını
    implement etmek zorundadır. robots.txt ve rate limiting otomatik uygulanır.
    """

    market_slug: str = ""
    base_url: str = ""

    def __init__(self):
        self._robots_parser: Optional[RobotFileParser] = None
        self._last_request_time: float = 0.0
        self._session: Optional[aiohttp.ClientSession] = None
        self._delay = settings.SCRAPER_REQUEST_DELAY_SECONDS

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def run(self) -> list[ScrapedCatalog]:
        """Ana giriş noktası. robots.txt kontrol + katalog çekme + parse."""
        async with aiohttp.ClientSession(
            headers={"User-Agent": settings.USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=settings.SCRAPER_TIMEOUT_SECONDS),
        ) as session:
            self._session = session
            await self._load_robots_txt()
            catalog_urls = await self.fetch_catalog_urls()
            results = []
            for url in catalog_urls:
                try:
                    catalog = await self.parse_catalog(url)
                    results.append(catalog)
                except Exception as exc:
                    logger.error(
                        "[%s] Katalog parse hatası: %s | URL: %s",
                        self.market_slug, exc, url, exc_info=True
                    )
            return results

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    async def fetch_catalog_urls(self) -> list[str]:
        """Marketteki aktif katalog URL'lerini döndür."""
        ...

    @abstractmethod
    async def parse_catalog(self, url: str) -> ScrapedCatalog:
        """Tek bir katalog URL'sini parse ederek ScrapedCatalog döndür."""
        ...

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """robots.txt + rate limit uygulayan GET wrapper'ı."""
        if not self._can_fetch(url):
            raise PermissionError(
                f"[{self.market_slug}] robots.txt bu URL'yi engelledi: {url}"
            )
        await self._rate_limit()

        retries = settings.SCRAPER_MAX_RETRIES
        for attempt in range(1, retries + 1):
            try:
                resp = await self._session.get(url, **kwargs)
                if resp.status == 503:
                    wait = 2 ** attempt
                    logger.warning(
                        "[%s] 503 alındı, %ds bekleniyor (deneme %d/%d)",
                        self.market_slug, wait, attempt, retries
                    )
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp
            except aiohttp.ClientResponseError as exc:
                if attempt == retries:
                    raise
                logger.warning(
                    "[%s] HTTP hatası %d, yeniden deneniyor (%d/%d): %s",
                    self.market_slug, exc.status, attempt, retries, url
                )
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError(f"[{self.market_slug}] Tüm denemeler başarısız: {url}")

    async def _rate_limit(self):
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._delay:
            await asyncio.sleep(self._delay - elapsed)
        self._last_request_time = time.monotonic()

    async def _load_robots_txt(self):
        robots_url = urljoin(self.base_url, "/robots.txt")
        try:
            async with self._session.get(robots_url) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    self._robots_parser = RobotFileParser()
                    self._robots_parser.parse(content.splitlines())
                    logger.info("[%s] robots.txt yüklendi.", self.market_slug)
        except Exception as exc:
            logger.warning(
                "[%s] robots.txt yüklenemedi: %s. Devam ediliyor.", self.market_slug, exc
            )

    def _can_fetch(self, url: str) -> bool:
        if self._robots_parser is None:
            return True
        return self._robots_parser.can_fetch(settings.USER_AGENT, url)
