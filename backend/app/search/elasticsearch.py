"""
Elasticsearch indeksleme ve arama modülü.
Türkçe morfoloji analizi + fuzzy search + eşanlamlı kelime desteği.
Sonuçlar her zaman unit_price_tl (birim fiyat) bazında ucuzdan pahalıya sıralanır.
"""

import logging
from typing import Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk

from app.config import settings

logger = logging.getLogger(__name__)

INDEX_NAME = settings.ELASTICSEARCH_INDEX_PRODUCTS

# Türkçe analiz ayarları: Zemberek veya ICU analyzer
INDEX_SETTINGS = {
    "settings": {
        "number_of_shards": 2,
        "number_of_replicas": 1,
        "analysis": {
            "analyzer": {
                "turkish_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "turkish_stop",
                        "turkish_stemmer",
                        "asciifolding",
                    ],
                },
                "turkish_search_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "turkish_stop",
                        "turkish_stemmer",
                        "asciifolding",
                        "synonym_filter",
                    ],
                },
            },
            "filter": {
                "turkish_stop": {
                    "type": "stop",
                    "stopwords": "_turkish_",
                },
                "turkish_stemmer": {
                    "type": "stemmer",
                    "language": "turkish",
                },
                "synonym_filter": {
                    "type": "synonym",
                    "synonyms": [
                        "süt, milk",
                        "ekmek, bread",
                        "yoğurt, yogurt",
                        "makarna, pasta",
                        "sabun, soap",
                        "deterjan, detergent",
                        "şampuan, shampoo",
                        "peynir, cheese",
                        "tavuk, chicken",
                        "et, meat, kıyma",
                    ],
                },
            },
        },
    },
    "mappings": {
        "properties": {
            "product_id": {"type": "integer"},
            "canonical_product_id": {"type": "integer"},
            "market_id": {"type": "integer"},
            "market_name": {"type": "keyword"},
            "market_slug": {"type": "keyword"},
            "name": {
                "type": "text",
                "analyzer": "turkish_analyzer",
                "search_analyzer": "turkish_search_analyzer",
                "fields": {
                    "keyword": {"type": "keyword"},
                    "suggest": {"type": "completion"},
                },
            },
            "brand": {
                "type": "text",
                "analyzer": "turkish_analyzer",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "category": {"type": "keyword"},
            "price_tl": {"type": "float"},
            "original_price_tl": {"type": "float"},
            "discount_pct": {"type": "float"},
            "unit_price_tl": {"type": "float"},  # Sıralama için kritik
            "unit_type": {"type": "keyword"},
            "unit_size": {"type": "float"},
            "image_url": {"type": "keyword", "index": False},
            "valid_from": {"type": "date"},
            "valid_until": {"type": "date"},
            "is_active": {"type": "boolean"},
        }
    },
}


class ProductSearchClient:
    def __init__(self):
        self._client: Optional[AsyncElasticsearch] = None

    @property
    def client(self) -> AsyncElasticsearch:
        if self._client is None:
            self._client = AsyncElasticsearch(
                [settings.ELASTICSEARCH_URL],
                retry_on_timeout=True,
                max_retries=3,
            )
        return self._client

    async def ensure_index(self) -> None:
        """Index yoksa oluştur, varsa ayarları güncelle."""
        try:
            exists = await self.client.indices.exists(index=INDEX_NAME)
            if not exists:
                await self.client.indices.create(index=INDEX_NAME, body=INDEX_SETTINGS)
                logger.info("Elasticsearch index oluşturuldu: %s", INDEX_NAME)
            else:
                logger.debug("Index zaten mevcut: %s", INDEX_NAME)
        except Exception as exc:
            logger.error("Index oluşturma hatası: %s", exc, exc_info=True)
            raise

    async def index_products(self, products: list[dict]) -> int:
        """Toplu ürün indeksleme (bulk insert/update)."""
        if not products:
            return 0

        actions = [
            {
                "_index": INDEX_NAME,
                "_id": p["product_id"],
                "_source": p,
            }
            for p in products
        ]
        success, errors = await async_bulk(
            self.client,
            actions,
            raise_on_error=False,
            stats_only=False,
        )
        if errors:
            logger.warning("Bulk index hataları: %d hata", len(errors))
        logger.info("Elasticsearch: %d ürün indekslendi.", success)
        return success

    async def search(
        self,
        query: str,
        market_slugs: Optional[list[str]] = None,
        category: Optional[str] = None,
        max_price_tl: Optional[float] = None,
        min_discount_pct: Optional[float] = None,
        from_: int = 0,
        size: int = 20,
    ) -> dict:
        """
        Türkçe fuzzy arama.
        Sonuçlar unit_price_tl bazında ucuzdan pahalıya sıralanır.
        """
        must = [
            {
                "multi_match": {
                    "query": query,
                    "fields": ["name^3", "brand^2", "category"],
                    "fuzziness": "AUTO",
                    "prefix_length": 1,
                    "analyzer": "turkish_search_analyzer",
                }
            },
            {"term": {"is_active": True}},
        ]

        filters = []
        if market_slugs:
            filters.append({"terms": {"market_slug": market_slugs}})
        if category:
            filters.append({"term": {"category": category}})
        if max_price_tl is not None:
            filters.append({"range": {"price_tl": {"lte": max_price_tl}}})
        if min_discount_pct is not None:
            filters.append({"range": {"discount_pct": {"gte": min_discount_pct}}})

        dsl = {
            "query": {
                "bool": {
                    "must": must,
                    "filter": filters,
                }
            },
            "sort": [
                {"unit_price_tl": {"order": "asc"}},
                "_score",
            ],
            "from": from_,
            "size": size,
            "highlight": {
                "fields": {
                    "name": {"fragment_size": 100, "number_of_fragments": 1}
                }
            },
        }

        try:
            response = await self.client.search(index=INDEX_NAME, body=dsl)
            return self._format_response(response)
        except Exception as exc:
            logger.error("Elasticsearch arama hatası: %s", exc, exc_info=True)
            raise

    async def suggest(self, prefix: str, size: int = 5) -> list[str]:
        """Otomatik tamamlama önerileri."""
        dsl = {
            "suggest": {
                "product_suggest": {
                    "prefix": prefix,
                    "completion": {
                        "field": "name.suggest",
                        "size": size,
                        "fuzzy": {"fuzziness": 1},
                    },
                }
            }
        }
        try:
            response = await self.client.search(index=INDEX_NAME, body=dsl)
            suggestions = response["suggest"]["product_suggest"][0]["options"]
            return [s["text"] for s in suggestions]
        except Exception as exc:
            logger.warning("Öneri hatası: %s", exc)
            return []

    @staticmethod
    def _format_response(raw: dict) -> dict:
        hits = raw.get("hits", {})
        return {
            "total": hits.get("total", {}).get("value", 0),
            "products": [
                {
                    **h["_source"],
                    "highlight": h.get("highlight", {}),
                    "score": h["_score"],
                }
                for h in hits.get("hits", [])
            ],
        }

    async def close(self):
        if self._client:
            await self._client.close()


# Singleton instance
search_client = ProductSearchClient()
