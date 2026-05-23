"""
Ürün Tekilleştirme (Entity Resolution) Pipeline.

3 aşamalı strateji:
1. Kural Tabanlı: Barkod eşleşmesi, tam isim eşleşmesi (normalizasyon sonrası)
2. NLP Embedding: sentence-transformers cosine similarity (eşik: 0.85)
3. LLM Doğrulama: GPT-4o ile şüpheli eşleşmeleri onayla/reddet
"""

import logging
from dataclasses import dataclass
from typing import Optional

from app.config import settings
from app.utils.turkish import normalize_text

logger = logging.getLogger(__name__)

# Cosine similarity eşiği: bu değerin üzerindekiler "aynı ürün" adayı
EMBEDDING_THRESHOLD = 0.85
# LLM'e gönderilecek "şüpheli eşleşme" bandı
LLM_REVIEW_LOWER = 0.70
LLM_REVIEW_UPPER = 0.85


@dataclass
class ResolutionCandidate:
    canonical_id: Optional[int]
    raw_name: str
    normalized_name: str
    similarity_score: float
    method: str  # "barcode", "exact", "embedding", "llm"
    is_match: bool


class EntityResolutionPipeline:
    def __init__(self):
        self._model = None  # Lazy load

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
                logger.info("SentenceTransformer modeli yüklendi.")
            except ImportError:
                logger.error("sentence-transformers kurulu değil.")
                raise
        return self._model

    async def resolve(
        self,
        raw_name: str,
        barcode: Optional[str],
        unit_type: Optional[str],
        unit_size: Optional[float],
        existing_canonicals: list[dict],
    ) -> ResolutionCandidate:
        """
        Ham ürün adını mevcut canonical'larla eşleştir.
        existing_canonicals: [{"id": 1, "normalized_name": "...", "barcode": "..."}]
        """
        normalized = normalize_text(raw_name)

        # Aşama 1: Barkod eşleşmesi (en güvenilir)
        if barcode:
            for canon in existing_canonicals:
                if canon.get("barcode") == barcode:
                    logger.debug("Barkod eşleşmesi: %s -> canonical %d", raw_name, canon["id"])
                    return ResolutionCandidate(
                        canonical_id=canon["id"],
                        raw_name=raw_name,
                        normalized_name=normalized,
                        similarity_score=1.0,
                        method="barcode",
                        is_match=True,
                    )

        # Aşama 2: Tam isim eşleşmesi (normalize edilmiş)
        for canon in existing_canonicals:
            if canon.get("normalized_name") == normalized:
                return ResolutionCandidate(
                    canonical_id=canon["id"],
                    raw_name=raw_name,
                    normalized_name=normalized,
                    similarity_score=1.0,
                    method="exact",
                    is_match=True,
                )

        # Aşama 3: Embedding benzerliği
        try:
            best_match = await self._embedding_match(normalized, existing_canonicals)
            if best_match and best_match.similarity_score >= EMBEDDING_THRESHOLD:
                return best_match

            # LLM doğrulama bandında mı?
            if (
                best_match
                and LLM_REVIEW_LOWER <= best_match.similarity_score < LLM_REVIEW_UPPER
                and settings.OPENAI_API_KEY
            ):
                confirmed = await self._llm_verify(raw_name, best_match)
                best_match.method = "llm"
                best_match.is_match = confirmed
                return best_match

        except Exception as exc:
            logger.warning("Embedding eşleştirme hatası: %s", exc)

        # Eşleşme bulunamadı -> yeni canonical oluşturulacak
        return ResolutionCandidate(
            canonical_id=None,
            raw_name=raw_name,
            normalized_name=normalized,
            similarity_score=0.0,
            method="none",
            is_match=False,
        )

    async def _embedding_match(
        self, normalized_name: str, candidates: list[dict]
    ) -> Optional[ResolutionCandidate]:
        if not candidates:
            return None

        import asyncio
        import numpy as np

        model = self._get_model()
        candidate_names = [c.get("normalized_name", "") for c in candidates]

        def _compute():
            query_emb = model.encode([normalized_name], normalize_embeddings=True)
            cand_embs = model.encode(candidate_names, normalize_embeddings=True)
            # Cosine similarity: dot product of normalized vectors
            scores = (query_emb @ cand_embs.T).flatten()
            best_idx = int(scores.argmax())
            return best_idx, float(scores[best_idx])

        best_idx, best_score = await asyncio.to_thread(_compute)
        best_canon = candidates[best_idx]

        return ResolutionCandidate(
            canonical_id=best_canon.get("id"),
            raw_name=normalized_name,
            normalized_name=normalized_name,
            similarity_score=best_score,
            method="embedding",
            is_match=best_score >= EMBEDDING_THRESHOLD,
        )

    async def _llm_verify(
        self, raw_name: str, candidate: ResolutionCandidate
    ) -> bool:
        """GPT-4o ile iki ürün adının aynı ürün olup olmadığını doğrula."""
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            prompt = (
                f"Aşağıdaki iki ürün adı aynı ürünü mü temsil ediyor? "
                f"Yalnızca 'evet' veya 'hayır' olarak cevapla.\n"
                f"Ürün 1: {raw_name}\n"
                f"Ürün 2: {candidate.normalized_name}"
            )
            response = await client.chat.completions.create(
                model="gpt-4o",
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            answer = response.choices[0].message.content.strip().lower()
            return "evet" in answer
        except Exception as exc:
            logger.error("LLM doğrulama hatası: %s", exc)
            return False
