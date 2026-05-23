"""
PDF'den ürün verisi çıkarma pipeline'ı.
Strateji: pdfplumber (metin tabanlı) -> Tesseract OCR (görüntü tabanlı) -> GPT-4o Vision (fallback)
"""

import asyncio
import base64
import io
import json
import logging
from typing import Optional

import pdfplumber

from app.config import settings
from app.scrapers.base import ScrapedProduct
from app.utils.turkish import parse_price_tl, parse_unit

logger = logging.getLogger(__name__)


async def extract_products_from_pdf(
    pdf_bytes: bytes,
    market_slug: str = "unknown",
    use_ai_fallback: bool = True,
) -> list[ScrapedProduct]:
    """
    Ana PDF ürün çıkarma fonksiyonu.
    1. pdfplumber ile metin tabanlı çıkarma dene
    2. Başarısız/az ürün çıkarıldıysa Tesseract OCR
    3. OCR de yetersizse GPT-4o Vision (ücretli, son çare)
    """
    products: list[ScrapedProduct] = []

    try:
        products = await _extract_with_pdfplumber(pdf_bytes, market_slug)
        if len(products) >= 3:
            logger.info("[%s] pdfplumber: %d ürün çıkarıldı.", market_slug, len(products))
            return products
    except Exception as exc:
        logger.warning("[%s] pdfplumber hatası: %s", market_slug, exc)

    # pdfplumber başarısız -> Tesseract
    try:
        products = await _extract_with_tesseract(pdf_bytes, market_slug)
        if len(products) >= 3:
            logger.info("[%s] Tesseract OCR: %d ürün.", market_slug, len(products))
            return products
    except Exception as exc:
        logger.warning("[%s] Tesseract hatası: %s", market_slug, exc)

    # Son çare: GPT-4o Vision
    if use_ai_fallback and settings.OPENAI_API_KEY:
        try:
            products = await _extract_with_gpt4o_vision(pdf_bytes, market_slug)
            logger.info("[%s] GPT-4o Vision: %d ürün.", market_slug, len(products))
        except Exception as exc:
            logger.error("[%s] GPT-4o Vision hatası: %s", market_slug, exc)

    return products


async def _extract_with_pdfplumber(
    pdf_bytes: bytes, market_slug: str
) -> list[ScrapedProduct]:
    """pdfplumber ile metin tabanlı PDF parse."""
    products = []

    def _sync_extract():
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Tablo varsa tablo satırlarından çıkar
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            if not row or not any(row):
                                continue
                            product = _parse_table_row(row, page_num)
                            if product:
                                products.append(product)
                else:
                    # Ham metin bloğundan çıkar
                    text = page.extract_text() or ""
                    page_products = _parse_text_block(text, page_num)
                    products.extend(page_products)
        return products

    return await asyncio.to_thread(_sync_extract)


async def _extract_with_tesseract(
    pdf_bytes: bytes, market_slug: str
) -> list[ScrapedProduct]:
    """
    pdf2image + pytesseract ile OCR tabanlı çıkarma.
    Türkçe karakter desteği için 'tur' dil paketi gerekli.
    """
    try:
        import pytesseract
        from pdf2image import convert_from_bytes
        from PIL import Image
    except ImportError:
        logger.error("pytesseract/pdf2image/Pillow kurulu değil.")
        return []

    def _sync_ocr():
        prods = []
        images: list[Image.Image] = convert_from_bytes(pdf_bytes, dpi=200)
        for page_num, img in enumerate(images, start=1):
            text = pytesseract.image_to_string(
                img,
                lang="tur",
                config="--psm 6 --oem 3",
            )
            page_prods = _parse_text_block(text, page_num)
            prods.extend(page_prods)
        return prods

    return await asyncio.to_thread(_sync_ocr)


async def _extract_with_gpt4o_vision(
    pdf_bytes: bytes, market_slug: str
) -> list[ScrapedProduct]:
    """
    OpenAI GPT-4o Vision ile PDF sayfalarını analiz et.
    Sadece diğer yöntemler yetersiz kaldığında kullanılır (maliyet yönetimi).
    """
    try:
        import openai
        from pdf2image import convert_from_bytes
    except ImportError:
        logger.error("openai/pdf2image kurulu değil.")
        return []

    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    products = []

    def _convert_pdf():
        return convert_from_bytes(pdf_bytes, dpi=150, first_page=1, last_page=5)

    images = await asyncio.to_thread(_convert_pdf)

    for page_num, img in enumerate(images, start=1):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        prompt = (
            "Bu bir Türk marketi indirim kataloğu sayfasıdır. "
            "Sayfadaki tüm ürünleri JSON array olarak çıkar. "
            "Her ürün için şu alanları doldur: "
            '{"raw_name": "...", "raw_price": "...", "raw_unit": "...", "raw_discount_text": "..."}. '
            "Fiyatları Türk Lirası formatında koru (virgüllü: 14,99). "
            "Sadece JSON array döndür, başka açıklama ekleme."
        )

        try:
            response = await client.chat.completions.create(
                model="gpt-4o",
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_b64}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
            )
            raw_json = response.choices[0].message.content.strip()
            # JSON bloğu varsa sarmayı temizle
            if raw_json.startswith("```"):
                raw_json = raw_json.split("```")[1]
                if raw_json.startswith("json"):
                    raw_json = raw_json[4:]

            items = json.loads(raw_json)
            for item in items:
                if item.get("raw_name"):
                    products.append(ScrapedProduct(
                        raw_name=item["raw_name"],
                        raw_price=item.get("raw_price"),
                        raw_unit=item.get("raw_unit"),
                        raw_discount_text=item.get("raw_discount_text"),
                        page_number=page_num,
                    ))
        except (json.JSONDecodeError, KeyError, Exception) as exc:
            logger.warning("[%s] GPT-4o sayfa %d parse hatası: %s", market_slug, page_num, exc)
            continue

    return products


def _parse_table_row(row: list, page_num: int) -> Optional[ScrapedProduct]:
    """PDF tablo satırından ürün parse et."""
    non_empty = [str(c).strip() for c in row if c and str(c).strip()]
    if len(non_empty) < 1:
        return None

    name = non_empty[0]
    price = non_empty[1] if len(non_empty) > 1 else None
    unit = non_empty[2] if len(non_empty) > 2 else None

    # Minimum isim uzunluğu kontrolü
    if len(name) < 3:
        return None

    return ScrapedProduct(
        raw_name=name,
        raw_price=price,
        raw_unit=unit,
        page_number=page_num,
    )


def _parse_text_block(text: str, page_num: int) -> list[ScrapedProduct]:
    """
    Ham metin bloğundan ürün satırlarını çıkar.
    TL fiyat pattern'ı: sayı + virgül/nokta + sayı + TL/₺
    """
    import re
    products = []
    price_pattern = re.compile(
        r"([\d]{1,5}[,.][\d]{2})\s*(?:TL|₺|tl)", re.IGNORECASE
    )

    lines = text.split("\n")
    for i, line in enumerate(lines):
        line = line.strip()
        if not line or len(line) < 3:
            continue
        price_match = price_pattern.search(line)
        if not price_match:
            continue

        raw_price = price_match.group(0)
        raw_name = line[: price_match.start()].strip()

        if not raw_name or len(raw_name) < 3:
            # Fiyat satırının önceki satırı ürün adı olabilir
            if i > 0 and lines[i - 1].strip():
                raw_name = lines[i - 1].strip()

        if raw_name and len(raw_name) >= 3:
            products.append(ScrapedProduct(
                raw_name=raw_name,
                raw_price=raw_price,
                page_number=page_num,
            ))

    return products
