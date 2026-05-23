"""
Türkçe metin normalizasyon yardımcıları.
- Büyük/küçük harf: Python'un standart upper/lower'ı İ/ı'yı yanlış işler.
- TL fiyat parse: "14,99 TL", "14.99", "14,99" -> float 14.99
- Birim normalizasyonu: "500 gr" -> ("g", 500.0)
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Türkçe karakter dönüşüm tabloları
_TR_UPPER_MAP = str.maketrans("çğıöşü", "ÇĞİÖŞÜ")
_TR_LOWER_MAP = str.maketrans("ÇĞİÖŞÜ", "çğıöşü")

# Birim eşleştirme sözlüğü
_UNIT_NORMALIZE = {
    "gr": "g", "gram": "g",
    "kg": "kg", "kilogram": "kg", "kilo": "kg",
    "ml": "ml", "mililitre": "ml",
    "lt": "lt", "ltr": "lt", "litre": "lt", "l": "lt",
    "adet": "adet", "ad": "adet", "pcs": "adet",
    "paket": "paket", "pkt": "paket", "pk": "paket",
    "deste": "deste",
}


def tr_upper(text: str) -> str:
    """Türkçe farkında büyük harf: 'istanbul' -> 'İSTANBUL'."""
    return text.translate(_TR_UPPER_MAP).upper()


def tr_lower(text: str) -> str:
    """Türkçe farkında küçük harf: 'İSTANBUL' -> 'istanbul'."""
    return text.translate(_TR_LOWER_MAP).lower()


def normalize_text(text: str) -> str:
    """
    Arama/eşleştirme için metin normalizasyonu.
    'Sütaş SÜZME YOĞURT 1KG' -> 'sutaş suzme yogurt 1kg'
    """
    if not text:
        return ""
    # Türkçe küçük harfe çevir
    text = tr_lower(text.strip())
    # Fazla boşlukları temizle
    text = re.sub(r"\s+", " ", text)
    return text


def parse_price_tl(raw: str) -> Optional[float]:
    """
    Ham OCR fiyat metnini float'a çevirir.
    Örnekler:
        '14,99 TL' -> 14.99
        '14.99'    -> 14.99
        '900,0'    -> 900.0  (OCR 90,0 yerine 900,0 okursa bölüm kontrolü)
        '1.499,00' -> 1499.0 (binlik ayraç)
    Edge case: OCR bazen ondalık ayraç olarak nokta kullanır (Türk standartı virgül).
    """
    if not raw:
        return None
    raw = raw.strip().upper().replace("TL", "").replace("₺", "").strip()

    # Binlik nokta + ondalık virgül: "1.499,00"
    if re.match(r"^\d{1,3}(\.\d{3})+(,\d+)?$", raw):
        raw = raw.replace(".", "").replace(",", ".")
    else:
        # Tekil virgül -> ondalık virgül: "14,99" -> "14.99"
        raw = raw.replace(",", ".")

    raw = re.sub(r"[^\d.]", "", raw)

    try:
        value = float(raw)
        # Mantık kontrolü: 0 veya aşırı yüksek fiyat uyarısı
        if value <= 0:
            logger.warning("parse_price_tl: Sıfır veya negatif fiyat: %s", raw)
            return None
        if value > 10000:
            logger.warning("parse_price_tl: Şüpheli yüksek fiyat (OCR hatası?): %.2f", value)
        return value
    except ValueError:
        logger.error("parse_price_tl: Float'a çevrilemiyor: %s", raw)
        return None


def parse_unit(raw_unit: str) -> tuple[Optional[str], Optional[float]]:
    """
    Ham birim metnini (tip, miktar) tuple'ına çevirir.
    Örnekler:
        '500 gr'  -> ('g', 500.0)
        '1 kg'    -> ('kg', 1000.0)  <- g cinsinden normalize
        '1.5 lt'  -> ('lt', 1500.0) <- ml cinsinden normalize
        '6 adet'  -> ('adet', 6.0)
    """
    if not raw_unit:
        return None, None

    raw = tr_lower(raw_unit.strip())
    # Sayı ve birimi ayır: "500gr", "500 gr", "1,5 lt"
    match = re.match(r"^([\d.,]+)\s*([a-züğışçö]+)$", raw)
    if not match:
        return None, None

    qty_str = match.group(1).replace(",", ".")
    unit_str = match.group(2).strip()

    try:
        qty = float(qty_str)
    except ValueError:
        return None, None

    normalized_unit = _UNIT_NORMALIZE.get(unit_str)
    if not normalized_unit:
        return None, None

    # Büyük birime normalize: kg -> g cinsinden sakla
    if normalized_unit == "kg":
        qty_g = qty * 1000
        return "g", qty_g
    if normalized_unit == "lt":
        qty_ml = qty * 1000
        return "ml", qty_ml

    return normalized_unit, qty


def compute_unit_price(price_tl: float, unit_type: str, unit_size: float) -> Optional[float]:
    """
    100g veya 100ml başına fiyat hesaplar.
    Bu değer tüm aramalarda ucuzdan pahalıya sıralama için kullanılır.
    """
    if not price_tl or not unit_size or unit_size <= 0:
        return None
    if unit_type in ("g", "ml"):
        return round((price_tl / unit_size) * 100, 4)
    if unit_type in ("kg", "lt"):
        # unit_size zaten gram/ml cinsinden tutuluyorsa:
        return round((price_tl / unit_size) * 100, 4)
    # Adet bazlı ürünler için birim fiyat = ürün fiyatı
    return round(price_tl, 4)
