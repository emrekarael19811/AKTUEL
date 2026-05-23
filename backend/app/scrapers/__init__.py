from app.scrapers.base import BaseScraper, ScrapedCatalog, ScrapedProduct
from app.scrapers.migros import MigrosScraper
from app.scrapers.bim import BimScraper
from app.scrapers.a101 import A101Scraper
from app.scrapers.sok import SokScraper
from app.scrapers.carrefoursa import CarrefoursaScraper

SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "migros": MigrosScraper,
    "bim": BimScraper,
    "a101": A101Scraper,
    "sok": SokScraper,
    "carrefoursa": CarrefoursaScraper,
}

__all__ = [
    "BaseScraper", "ScrapedCatalog", "ScrapedProduct",
    "MigrosScraper", "BimScraper", "A101Scraper", "SokScraper", "CarrefoursaScraper",
    "SCRAPER_REGISTRY",
]
