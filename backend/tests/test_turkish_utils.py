"""
Türkçe yardımcı fonksiyonlar için unit testler.
pytest tests/test_turkish_utils.py ile çalıştır.
"""

import pytest
from app.utils.turkish import (
    tr_upper, tr_lower, normalize_text,
    parse_price_tl, parse_unit, compute_unit_price,
)


class TestTrCase:
    def test_tr_upper_dotted_i(self):
        assert tr_upper("istanbul") == "İSTANBUL"

    def test_tr_lower_dotless_i(self):
        assert tr_lower("İSTANBUL") == "istanbul"

    def test_tr_upper_all_chars(self):
        assert tr_upper("çğışöü") == "ÇĞİŞÖÜ"


class TestParsePriceTl:
    def test_comma_decimal(self):
        assert parse_price_tl("14,99 TL") == pytest.approx(14.99)

    def test_dot_decimal(self):
        assert parse_price_tl("14.99") == pytest.approx(14.99)

    def test_lira_sign(self):
        assert parse_price_tl("₺29,90") == pytest.approx(29.90)

    def test_thousands_separator(self):
        assert parse_price_tl("1.499,00 TL") == pytest.approx(1499.00)

    def test_zero_returns_none(self):
        assert parse_price_tl("0,00 TL") is None

    def test_empty_returns_none(self):
        assert parse_price_tl("") is None

    def test_garbage_returns_none(self):
        assert parse_price_tl("ADET") is None

    def test_suspicious_high_price_still_returns(self):
        # 900,0 OCR hatası olsa bile değeri döndür (loglama yapılır)
        result = parse_price_tl("900,0")
        assert result == pytest.approx(900.0)


class TestParseUnit:
    def test_gram(self):
        assert parse_unit("500 gr") == ("g", 500.0)

    def test_kilogram_to_gram(self):
        unit_type, qty = parse_unit("1 kg")
        assert unit_type == "g"
        assert qty == pytest.approx(1000.0)

    def test_litre_to_ml(self):
        unit_type, qty = parse_unit("1,5 lt")
        assert unit_type == "ml"
        assert qty == pytest.approx(1500.0)

    def test_ml_stays_ml(self):
        assert parse_unit("330 ml") == ("ml", 330.0)

    def test_adet(self):
        assert parse_unit("6 adet") == ("adet", 6.0)

    def test_empty_returns_none_none(self):
        assert parse_unit("") == (None, None)

    def test_unknown_unit_returns_none_none(self):
        assert parse_unit("5 pieces") == (None, None)


class TestComputeUnitPrice:
    def test_100g_price(self):
        # 500g ürün 14.99 TL -> 100g fiyatı = 2.998 TL
        result = compute_unit_price(14.99, "g", 500.0)
        assert result == pytest.approx(2.998, rel=0.001)

    def test_100ml_price(self):
        # 1000ml ürün 25 TL -> 100ml = 2.50 TL
        result = compute_unit_price(25.0, "ml", 1000.0)
        assert result == pytest.approx(2.5)

    def test_zero_size_returns_none(self):
        assert compute_unit_price(10.0, "g", 0.0) is None

    def test_none_price_returns_none(self):
        assert compute_unit_price(None, "g", 500.0) is None
