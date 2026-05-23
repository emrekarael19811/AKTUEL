# AKTÜEL – Türkiye Süpermarket İndirim Takip Platformu

BİM, A101, Migros, ŞOK ve CarrefourSA haftalık aktüel kataloglarını toplar,
indeksler, karşılaştırır ve kişiselleştirilmiş fiyat alarmı bildirileri gönderir.

## Mimari Özet

```
┌──────────────────────────────────────────────────────────┐
│  Frontend (Next.js 14)        Mobile (React Native/Expo) │
│  Web: /search, /markets       Push bildirimleri (FCM)    │
└────────────────────┬─────────────────────────────────────┘
                     │ REST API
┌────────────────────▼─────────────────────────────────────┐
│            FastAPI Backend (Python 3.11)                  │
│   /api/v1/search • /markets • /catalogs • /watchlist     │
│   Celery + Redis (Scraping & Bildirim görevleri)          │
└──────┬──────────────┬──────────────┬────────────────┬────┘
       │              │              │                │
  Supabase       Elasticsearch    Redis Cache    Firebase FCM
 (PostgreSQL)   (Türkçe Arama)  (Session/Task)  (Push Bildirim)
```

## Tech Stack

| Katman | Teknoloji |
|--------|-----------|
| Backend | Python 3.11, FastAPI, Celery, APScheduler |
| Web | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Mobil | React Native (Expo), TypeScript |
| Veritabanı | Supabase (PostgreSQL), SQLAlchemy |
| Arama | Elasticsearch 8 (Türkçe morfoloji) |
| Cache/Queue | Redis, Celery |
| AI/OCR | pdfplumber, Tesseract OCR, GPT-4o Vision |
| ML | sentence-transformers (Entity Resolution), Prophet (Tahmin) |
| Bildirim | Firebase Cloud Messaging (FCM) |
| Altyapı | Docker, Nginx, GitHub Actions |

## Hızlı Başlangıç

### 1. Ortam Değişkenleri

```bash
cp .env.example .env
# .env dosyasını Supabase ve diğer bilgilerle doldurun
```

### 2. Docker Compose ile Başlat

```bash
cd infrastructure
docker compose up -d
```

### 3. Veritabanı Seed

```bash
cd backend
python ../scripts/seed_markets.py
```

### 4. İlk Scraping

```bash
# Manuel tetikleme
docker exec aktuel-api python -c "
from app.tasks.scraping import scrape_market
scrape_market.delay('bim')
"
```

## Proje Yapısı

```
AKTUEL/
├── backend/
│   ├── app/
│   │   ├── models/          # SQLAlchemy ORM modelleri
│   │   ├── api/v1/          # FastAPI endpoint'leri
│   │   ├── scrapers/        # Market scraper'ları (BİM, A101, Migros...)
│   │   ├── ocr/             # PDF→ürün pipeline (pdfplumber + OCR + GPT-4o)
│   │   ├── ml/              # Entity Resolution + Katalog Tahmini
│   │   ├── search/          # Elasticsearch istemcisi
│   │   ├── tasks/           # Celery görevleri
│   │   └── utils/           # Türkçe yardımcılar (fiyat parse, birim)
│   ├── tests/               # pytest unit testleri
│   └── requirements.txt
├── frontend/
│   ├── web/                 # Next.js 14 web uygulaması
│   └── mobile/              # React Native (Expo)
├── infrastructure/
│   ├── docker-compose.yml
│   └── nginx/
├── scripts/
│   └── seed_markets.py      # Başlangıç market verisi
└── .github/workflows/ci.yml # GitHub Actions CI
```

## API Endpointleri

| Endpoint | Açıklama |
|----------|----------|
| `GET /api/v1/markets/` | Tüm marketler |
| `GET /api/v1/catalogs/` | Aktif kataloglar |
| `GET /api/v1/search/?q=süt` | Türkçe fuzzy arama |
| `GET /api/v1/search/suggest?q=sü` | Otomatik tamamlama |
| `GET /api/v1/products/` | Ürün listesi (birim fiyat sıralı) |
| `GET /api/v1/products/{id}/price-history` | Fiyat tarihçesi |
| `GET /api/v1/watchlist/` | Kullanıcı takip listesi |
| `POST /api/v1/watchlist/` | Ürün takibe al |

## Celery Görev Takvimi

| Market | Gün | Saat |
|--------|-----|------|
| BİM | Cuma | 08:00 |
| Migros | Cuma | 08:30 |
| A101 | Perşembe | 08:00 |
| ŞOK | Perşembe | 08:30 |
| CarrefourSA | Perşembe | 09:00 |
| Fiyat alarm kontrolü | Her saat | :00 |

## KVKK Uyumluluğu

- Kullanıcı verileri açık rıza (`kvkk_consent`) ile saklanır
- FCM token'lar şifreli ve silinebilir
- Kişisel veri içermeyen analitik ayrı tutulur
