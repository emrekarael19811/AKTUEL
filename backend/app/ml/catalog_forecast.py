"""
Katalog yayın tarihi tahmini - Facebook Prophet ile zaman serisi analizi.
BİM: Cuma, A101: Perşembe. Prophet bu döngüyü öğrenir ve bir sonraki tarihi tahmin eder.
Erken uyarı bildirimleri için katalog çıkmadan 2-3 gün önce bildir.
"""

import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Her market için varsayılan yayın günü (0=Pazartesi, 4=Cuma, 3=Perşembe)
MARKET_DEFAULT_WEEKDAY = {
    "bim": 4,      # Cuma
    "a101": 3,     # Perşembe
    "migros": 4,   # Cuma
    "sok": 3,      # Perşembe
    "carrefoursa": 3,
}

EARLY_ALERT_DAYS = 2  # Katalog çıkmadan 2 gün önce bildir


class CatalogForecast:
    def __init__(self, market_slug: str):
        self.market_slug = market_slug
        self._model = None

    def fit(self, catalog_dates: list[date]) -> None:
        """
        Geçmiş katalog yayın tarihlerinden Prophet modeli eğit.
        En az 2 tarih gerekli; az veri varsa rule-based fallback kullanılır.
        """
        if len(catalog_dates) < 2:
            logger.warning(
                "[%s] Yeterli tarih yok, rule-based tahmin kullanılacak.", self.market_slug
            )
            return

        try:
            from prophet import Prophet

            df = pd.DataFrame({
                "ds": pd.to_datetime(catalog_dates),
                "y": 1.0,
            })
            self._model = Prophet(
                weekly_seasonality=True,
                yearly_seasonality=False,
                daily_seasonality=False,
                interval_width=0.80,
            )
            self._model.fit(df)
            logger.info("[%s] Prophet modeli eğitildi: %d veri noktası.", self.market_slug, len(df))
        except ImportError:
            logger.error("prophet kurulu değil. pip install prophet")

    def predict_next(self, from_date: Optional[date] = None) -> date:
        """
        Bir sonraki katalog yayın tarihini tahmin et.
        Prophet model yoksa haftalık döngü kuralına göre hesapla.
        """
        today = from_date or date.today()

        if self._model is not None:
            try:
                future = self._model.make_future_dataframe(periods=14, freq="D")
                forecast = self._model.predict(future)
                future_dates = forecast[forecast["ds"] > pd.Timestamp(today)]
                if not future_dates.empty:
                    predicted = future_dates.iloc[0]["ds"].date()
                    logger.info("[%s] Prophet tahmini: %s", self.market_slug, predicted)
                    return predicted
            except Exception as exc:
                logger.warning("[%s] Prophet tahmin hatası: %s, fallback kullanılıyor.", self.market_slug, exc)

        return self._rule_based_next(today)

    def predict_early_alert_date(self, from_date: Optional[date] = None) -> date:
        """Bir sonraki kataloğun erken uyarı tarihini hesapla."""
        next_catalog = self.predict_next(from_date)
        return next_catalog - timedelta(days=EARLY_ALERT_DAYS)

    def _rule_based_next(self, from_date: date) -> date:
        """
        Haftalık döngü kuralına göre bir sonraki yayın gününü bul.
        Örn: BİM her Cuma -> bugün Salı ise 3 gün sonraki Cuma döndür.
        """
        target_weekday = MARKET_DEFAULT_WEEKDAY.get(self.market_slug, 4)
        days_ahead = (target_weekday - from_date.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7  # Bugünse bir sonraki haftaya git
        return from_date + timedelta(days=days_ahead)
