"""
Bildirim görevleri: Fiyat eşiği kontrolü ve FCM push gönderimi.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="tasks.check_price_alerts")
def check_price_alerts() -> dict:
    """
    Tüm aktif watchlist kayıtlarını tarayarak fiyat eşiği kontrolü yap.
    Celery Beat ile saatlik çalışır.
    """
    import asyncio
    return asyncio.run(_async_check_price_alerts())


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="tasks.send_push_notification",
)
def send_push_notification(
    self,
    user_id: str,
    fcm_token: str,
    title: str,
    body: str,
    data: dict = None,
) -> dict:
    import asyncio
    try:
        result = asyncio.run(
            _async_send_fcm(fcm_token, title, body, data or {})
        )
        return result
    except Exception as exc:
        logger.error("FCM gönderim hatası user=%s: %s", user_id, exc)
        raise self.retry(exc=exc)


async def _async_check_price_alerts() -> dict:
    from app.database import AsyncSessionLocal
    from app.models import Watchlist, ProductPrice, User
    from sqlalchemy import select
    from datetime import date

    sent = 0
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Watchlist, ProductPrice, User)
            .join(ProductPrice, Watchlist.canonical_product_id == ProductPrice.canonical_product_id)
            .join(User, Watchlist.user_id == User.id)
            .where(
                Watchlist.is_active == True,
                User.is_active == True,
                User.fcm_token.isnot(None),
                ProductPrice.valid_until >= date.today(),
            )
        )
        rows = result.all()

    for watchlist, price, user in rows:
        should_notify = False
        reason = ""

        if (
            watchlist.price_threshold_tl
            and price.price_tl <= watchlist.price_threshold_tl
        ):
            should_notify = True
            reason = f"Fiyat eşiği: {price.price_tl:.2f} TL ≤ {watchlist.price_threshold_tl:.2f} TL"

        elif (
            watchlist.unit_price_threshold_tl
            and price.unit_price_tl
            and price.unit_price_tl <= watchlist.unit_price_threshold_tl
        ):
            should_notify = True
            reason = f"Birim fiyat eşiği sağlandı"

        elif watchlist.notify_on_any_discount and price.discount_pct and price.discount_pct > 0:
            should_notify = True
            reason = f"%{price.discount_pct:.0f} indirim"

        if should_notify and user.fcm_token:
            send_push_notification.delay(
                user_id=user.id,
                fcm_token=user.fcm_token,
                title="İndirim Alarmı! 🎯",
                body=f"Takip ettiğiniz ürün indirimde! {reason}",
                data={
                    "canonical_product_id": str(watchlist.canonical_product_id),
                    "price_tl": str(price.price_tl),
                    "discount_pct": str(price.discount_pct or 0),
                },
            )
            sent += 1

    logger.info("Fiyat alarm kontrolü: %d bildirim gönderildi.", sent)
    return {"checked": len(rows), "sent": sent}


async def _async_send_fcm(
    fcm_token: str, title: str, body: str, data: dict
) -> dict:
    """Firebase Cloud Messaging ile push bildirim gönder."""
    from app.config import settings

    if not settings.FIREBASE_CREDENTIALS_PATH:
        logger.warning("Firebase credentials tanımlı değil.")
        return {"status": "skipped", "reason": "no_credentials"}

    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={str(k): str(v) for k, v in data.items()},
            token=fcm_token,
            android=messaging.AndroidConfig(priority="high"),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default")
                )
            ),
        )
        response_id = messaging.send(message)
        logger.info("FCM gönderildi: %s", response_id)
        return {"status": "sent", "message_id": response_id}
    except Exception as exc:
        logger.error("FCM hatası: %s", exc, exc_info=True)
        raise
