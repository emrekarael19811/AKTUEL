"""
Entity Resolution pipeline testleri.
"""

import pytest
from unittest.mock import AsyncMock, patch
from app.ml.entity_resolution import EntityResolutionPipeline, EMBEDDING_THRESHOLD


@pytest.mark.asyncio
async def test_barcode_match_wins():
    pipeline = EntityResolutionPipeline()
    candidates = [
        {"id": 1, "normalized_name": "sütaş süt 1lt", "barcode": "8690456789012"},
        {"id": 2, "normalized_name": "ülker bisküvi", "barcode": None},
    ]
    result = await pipeline.resolve(
        raw_name="SÜTAŞ SÜT 1 LT",
        barcode="8690456789012",
        unit_type="ml",
        unit_size=1000.0,
        existing_canonicals=candidates,
    )
    assert result.is_match is True
    assert result.canonical_id == 1
    assert result.method == "barcode"


@pytest.mark.asyncio
async def test_exact_name_match():
    pipeline = EntityResolutionPipeline()
    candidates = [
        {"id": 5, "normalized_name": "sütaş süt 1lt", "barcode": None},
    ]
    result = await pipeline.resolve(
        raw_name="Sütaş Süt 1lt",
        barcode=None,
        unit_type=None,
        unit_size=None,
        existing_canonicals=candidates,
    )
    assert result.is_match is True
    assert result.canonical_id == 5
    assert result.method == "exact"


@pytest.mark.asyncio
async def test_no_match_returns_none_canonical():
    pipeline = EntityResolutionPipeline()
    with patch.object(pipeline, "_embedding_match", new_callable=AsyncMock) as mock_emb:
        mock_emb.return_value = None
        result = await pipeline.resolve(
            raw_name="Tamamen yeni bir ürün XYZ123",
            barcode=None,
            unit_type=None,
            unit_size=None,
            existing_canonicals=[],
        )
    assert result.canonical_id is None
    assert result.is_match is False


@pytest.mark.asyncio
async def test_embedding_threshold():
    pipeline = EntityResolutionPipeline()
    from app.ml.entity_resolution import ResolutionCandidate
    low_score_candidate = ResolutionCandidate(
        canonical_id=99,
        raw_name="test",
        normalized_name="test",
        similarity_score=0.60,  # eşiğin altında
        method="embedding",
        is_match=False,
    )
    with patch.object(pipeline, "_embedding_match", new_callable=AsyncMock) as mock_emb:
        mock_emb.return_value = low_score_candidate
        result = await pipeline.resolve(
            raw_name="farklı bir ürün",
            barcode=None,
            unit_type=None,
            unit_size=None,
            existing_canonicals=[{"id": 99, "normalized_name": "test", "barcode": None}],
        )
    # Düşük skor -> eşleşme yok
    assert result.is_match is False
