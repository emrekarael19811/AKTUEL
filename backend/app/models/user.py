from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Enum, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class NotificationChannel(str, enum.Enum):
    PUSH = "push"
    EMAIL = "email"
    SMS = "sms"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)  # Supabase Auth UUID
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(100))
    fcm_token = Column(String(500))
    preferred_markets = Column(Text)  # JSON: [1, 3, 5]
    # KVKK: açık rıza
    kvkk_consent = Column(Boolean, default=False)
    kvkk_consent_at = Column(DateTime(timezone=True))
    marketing_consent = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    watchlist = relationship("Watchlist", back_populates="user", lazy="dynamic")
    notifications = relationship("Notification", back_populates="user", lazy="dynamic")


class Watchlist(Base):
    """Kullanıcının takip ettiği ürün/fiyat eşikleri."""
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    canonical_product_id = Column(
        Integer, ForeignKey("canonical_products.id"), nullable=False, index=True
    )
    price_threshold_tl = Column(Float)      # Bu fiyatın altına düşünce bildir
    unit_price_threshold_tl = Column(Float) # Birim fiyat eşiği
    notify_on_any_discount = Column(Boolean, default=True)
    notify_early = Column(Boolean, default=True)  # Katalog çıkmadan önce
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="watchlist")
    canonical_product = relationship("CanonicalProduct")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    watchlist_id = Column(Integer, ForeignKey("watchlist.id"), nullable=True)
    canonical_product_id = Column(Integer, ForeignKey("canonical_products.id"))
    market_id = Column(Integer, ForeignKey("markets.id"))
    channel = Column(Enum(NotificationChannel), default=NotificationChannel.PUSH)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING)
    title = Column(String(200))
    body = Column(Text)
    price_tl = Column(Float)
    discount_pct = Column(Float)
    fcm_message_id = Column(String(200))
    sent_at = Column(DateTime(timezone=True))
    read_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")
