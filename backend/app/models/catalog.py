from sqlalchemy import Column, String, Integer, Date, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class CatalogStatus(str, enum.Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    OCR_PROCESSING = "ocr_processing"
    PARSING = "parsing"
    INDEXING = "indexing"
    ACTIVE = "active"
    EXPIRED = "expired"
    FAILED = "failed"


class Catalog(Base):
    __tablename__ = "catalogs"

    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=False, index=True)
    valid_from = Column(Date, nullable=False, index=True)
    valid_until = Column(Date, nullable=False, index=True)
    pdf_url = Column(String(1000))
    local_pdf_path = Column(String(500))
    page_count = Column(Integer)
    status = Column(Enum(CatalogStatus), default=CatalogStatus.PENDING, index=True)
    ocr_engine = Column(String(50))  # "tesseract", "google_vision", "gpt4o"
    raw_product_count = Column(Integer, default=0)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    market = relationship("Market", back_populates="catalogs")
    raw_products = relationship("RawProduct", back_populates="catalog", lazy="dynamic")
