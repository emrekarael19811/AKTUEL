from sqlalchemy import Column, String, Integer, Boolean, Enum, Text, Float
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class ScraperType(str, enum.Enum):
    PDF = "pdf"
    WEB = "web"
    API = "api"


class Market(Base):
    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    website_url = Column(String(500), nullable=False)
    catalog_url = Column(String(500))
    logo_url = Column(String(500))
    scraper_type = Column(Enum(ScraperType), default=ScraperType.PDF)
    catalog_cycle_days = Column(Integer, default=7)
    # Türkiye'deki marketlerin yayın günleri: 0=Pzt...6=Paz
    catalog_publish_weekday = Column(Integer)
    is_active = Column(Boolean, default=True)
    robots_txt_url = Column(String(500))
    request_delay_seconds = Column(Float, default=2.0)
    notes = Column(Text)

    catalogs = relationship("Catalog", back_populates="market", lazy="dynamic")
