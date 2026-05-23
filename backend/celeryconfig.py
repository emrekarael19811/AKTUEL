"""
Celery yapılandırması ve Beat (cron) görev takvimi.
BİM Cuma, A101 Perşembe yayın döngüleri burada planlanır.
"""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "aktuel",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.scraping",
        "app.tasks.notifications",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Istanbul",
    enable_utc=False,
    worker_max_tasks_per_child=100,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        # Her Cuma 08:00 -> BİM, Migros
        "scrape-bim-friday": {
            "task": "tasks.scrape_market",
            "schedule": crontab(hour=8, minute=0, day_of_week=5),
            "args": ["bim"],
        },
        "scrape-migros-friday": {
            "task": "tasks.scrape_market",
            "schedule": crontab(hour=8, minute=30, day_of_week=5),
            "args": ["migros"],
        },
        # Her Perşembe 08:00 -> A101, ŞOK, CarrefourSA
        "scrape-a101-thursday": {
            "task": "tasks.scrape_market",
            "schedule": crontab(hour=8, minute=0, day_of_week=4),
            "args": ["a101"],
        },
        "scrape-sok-thursday": {
            "task": "tasks.scrape_market",
            "schedule": crontab(hour=8, minute=30, day_of_week=4),
            "args": ["sok"],
        },
        "scrape-carrefoursa-thursday": {
            "task": "tasks.scrape_market",
            "schedule": crontab(hour=9, minute=0, day_of_week=4),
            "args": ["carrefoursa"],
        },
        # Her saat fiyat alarm kontrolü
        "check-price-alerts-hourly": {
            "task": "tasks.check_price_alerts",
            "schedule": crontab(minute=0),
        },
    },
)
