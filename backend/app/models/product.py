from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date,
    ForeignKey, Text, ARRAY, Index, Enum, BigInteger
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector as VECTOR
import enum
from app.database import Base


class UnitType(str, enum.Enum):
    KG = "kg"
    G = "g"
    LT = "lt"
    ML = "ml"
    ADET = "adet"
    PAKET = "paket"
    DESTE = "deste"


class RawProduct(Base):
    __tablename__ = "raw_products"

    id = Column(BigInteger, primary_key=True, index=True)
    catalog_id = Column(Integer, ForeignKey("catalogs.id"), nullable=False, index=True)
    raw_name = Column(String(500), nullable=False)
    raw_price = Column(String(50))           # OCR'dan ham: "14,99 TL" / "14.99"
    raw_unit = Column(String(100))           # Ham birim: "1 kg", "500 gr"
    raw_discount_text = Column(String(200))  # "3 Al 2 Öde", "%30 İndirim"
    image_url = Column(String(1000))
    page_number = Column(Integer)
    canonical_product_id = Column(
        Integer, ForeignKey("canonical_products.id"), nullable=True, index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    catalog = relationship("Catalog", back_populates="raw_products")
    prices = relationship("ProductPrice", back_populates="raw_product")
    canonical_product = relationship("CanonicalProduct", back_populates="raw_products")


class CanonicalProduct(Base):
    __tablename__ = "canonical_products"

    id = Column(Integer, primary_key=True, index=True)
    normalized_name = Column(String(500), nullable=False, index=True)
    brand = Column(String(200), index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    barcode = Column(String(50), unique=True, nullable=True, index=True)
    unit_type = Column(Enum(UnitType))
    unit_size = Column(Float)             # 1.0 (kg), 500.0 (ml) vb.
    # pgvector: sentence-transformers 768-dim embedding
    embedding_vector = Column(VECTOR(768), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    raw_products = relationship("RawProduct", back_populates="canonical_product")
    prices = relationship("ProductPrice", back_populates="canonical_product")

    __table_args__ = (
        Index(
            "ix_canonical_products_embedding",
            embedding_vector,
            postgresql_using="ivfflat",
            postgresql_ops={"embedding_vector": "vector_cosine_ops"},
        ),
    )


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    icon_emoji = Column(String(10))


class ProductPrice(Base):
    """
    Time-series fiyat tablosu. TimescaleDB hypertable olarak yönetilir.
    """
    __tablename__ = "product_prices"

    id = Column(BigInteger, primary_key=True, index=True)
    raw_product_id = Column(BigInteger, ForeignKey("raw_products.id"), nullable=False)
    canonical_product_id = Column(
        Integer, ForeignKey("canonical_products.id"), nullable=True, index=True
    )
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=False, index=True)
    catalog_id = Column(Integer, ForeignKey("catalogs.id"), nullable=False)
    price_tl = Column(Float, nullable=False)          # Kampanya fiyatı
    original_price_tl = Column(Float)                 # Kampanya öncesi fiyat
    discount_pct = Column(Float)                      # % indirim oranı
    unit_price_tl = Column(Float, index=True)         # 100g / 100ml birim fiyat
    valid_from = Column(Date, nullable=False, index=True)
    valid_until = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    raw_product = relationship("RawProduct", back_populates="prices")
    canonical_product = relationship("CanonicalProduct", back_populates="prices")

    __table_args__ = (
        Index("ix_product_prices_valid_market", "valid_from", "market_id"),
        Index("ix_product_prices_canonical_valid", "canonical_product_id", "valid_from"),
    )
