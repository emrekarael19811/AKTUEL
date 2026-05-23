from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AKTUEL"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    # Supabase / PostgreSQL
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_ANON_KEY: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_INDEX_PRODUCTS: str = "aktuel_products"

    # AI / OCR
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_VISION_CREDENTIALS_PATH: Optional[str] = None
    TESSERACT_CMD: str = "/usr/bin/tesseract"

    # Firebase
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    FCM_SERVER_KEY: Optional[str] = None

    # Scraper
    SCRAPER_REQUEST_DELAY_SECONDS: float = 2.0
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_TIMEOUT_SECONDS: int = 30
    USER_AGENT: str = (
        "AKTUEL-Bot/1.0 (+https://aktuel.app/bot; "
        "indirim-takip-uygulamasi@aktuel.app)"
    )

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "https://aktuel.app",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
