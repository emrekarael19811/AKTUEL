-- AKTUEL Initial Schema Migration
-- Supabase GitHub entegrasyonu bu dosyayi otomatik uygular.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    slug        VARCHAR(100) UNIQUE NOT NULL,
    parent_id   INTEGER REFERENCES categories(id),
    icon_emoji  VARCHAR(10)
);

INSERT INTO categories (name, slug, icon_emoji) VALUES
    ('Süt & Süt Ürünleri',   'sut-urunleri',  '🥛'),
    ('Et & Şarküteri',       'et-sarküteri',  '🥩'),
    ('Meyve & Sebze',        'meyve-sebze',   '🥦'),
    ('Ekmek & Unlu Mamüller','ekmek-unlu',    '🍞'),
    ('İçecekler',            'icecekler',     '🥤'),
    ('Temizlik',             'temizlik',      '🧹'),
    ('Kişisel Bakım',        'kisisel-bakim', '🧴'),
    ('Dondurulmuş',          'dondurulmus',   '🧊'),
    ('Kahvaltılık',          'kahvaltilik',   '🍳'),
    ('Atıştırmalık',         'atistirmalik',  '🍿')
ON CONFLICT (slug) DO NOTHING;

CREATE TABLE IF NOT EXISTS markets (
    id                      SERIAL PRIMARY KEY,
    name                    VARCHAR(100) NOT NULL,
    slug                    VARCHAR(50)  UNIQUE NOT NULL,
    website_url             VARCHAR(500) NOT NULL,
    catalog_url             VARCHAR(500),
    logo_url                VARCHAR(500),
    scraper_type            VARCHAR(20)  DEFAULT 'pdf' CHECK (scraper_type IN ('pdf','web','api')),
    catalog_cycle_days      INTEGER      DEFAULT 7,
    catalog_publish_weekday INTEGER      CHECK (catalog_publish_weekday BETWEEN 0 AND 6),
    is_active               BOOLEAN      DEFAULT TRUE,
    robots_txt_url          VARCHAR(500),
    request_delay_seconds   FLOAT        DEFAULT 2.0,
    notes                   TEXT,
    created_at              TIMESTAMPTZ  DEFAULT NOW()
);

INSERT INTO markets (name, slug, website_url, catalog_url, scraper_type, catalog_cycle_days, catalog_publish_weekday) VALUES
    ('BİM',        'bim',        'https://www.bim.com.tr',        'https://www.bim.com.tr/Modules/ActuelProducts/ActuelProducts.aspx', 'web', 7, 4),
    ('A101',       'a101',       'https://www.a101.com.tr',       'https://www.a101.com.tr/a101-aktuel-urunler',                        'web', 7, 3),
    ('Migros',     'migros',     'https://www.migros.com.tr',     'https://www.migros.com.tr/kampanyalar/kataloglar',                   'pdf', 7, 4),
    ('ŞOK Market', 'sok',        'https://www.sokmarket.com.tr',  'https://www.sokmarket.com.tr/aktuel-urunler',                        'web', 7, 3),
    ('CarrefourSA','carrefoursa','https://www.carrefoursa.com',   'https://www.carrefoursa.com/kampanyalar/haftalik-indirim-katalogu',  'pdf', 7, 3)
ON CONFLICT (slug) DO NOTHING;

CREATE TABLE IF NOT EXISTS catalogs (
    id                  SERIAL PRIMARY KEY,
    market_id           INTEGER      NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    valid_from          DATE         NOT NULL,
    valid_until         DATE         NOT NULL,
    pdf_url             VARCHAR(1000),
    catalog_url         VARCHAR(1000),
    local_pdf_path      VARCHAR(500),
    page_count          INTEGER,
    status              VARCHAR(30)  DEFAULT 'pending'
                            CHECK (status IN ('pending','downloading','ocr_processing','parsing','indexing','active','expired','failed')),
    ocr_engine          VARCHAR(50),
    raw_product_count   INTEGER      DEFAULT 0,
    error_message       TEXT,
    created_at          TIMESTAMPTZ  DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER catalogs_updated_at
    BEFORE UPDATE ON catalogs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TABLE IF NOT EXISTS canonical_products (
    id               SERIAL PRIMARY KEY,
    normalized_name  VARCHAR(500) NOT NULL,
    brand            VARCHAR(200),
    category_id      INTEGER REFERENCES categories(id),
    barcode          VARCHAR(50) UNIQUE,
    unit_type        VARCHAR(20) CHECK (unit_type IN ('kg','g','lt','ml','adet','paket','deste')),
    unit_size        FLOAT,
    embedding_vector vector(768),
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw_products (
    id                    BIGSERIAL PRIMARY KEY,
    catalog_id            INTEGER      NOT NULL REFERENCES catalogs(id) ON DELETE CASCADE,
    raw_name              VARCHAR(500) NOT NULL,
    raw_price             VARCHAR(50),
    raw_unit              VARCHAR(100),
    raw_discount_text     VARCHAR(200),
    image_url             VARCHAR(1000),
    page_number           INTEGER,
    canonical_product_id  INTEGER REFERENCES canonical_products(id),
    created_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS product_prices (
    id                    BIGSERIAL PRIMARY KEY,
    raw_product_id        BIGINT  NOT NULL REFERENCES raw_products(id) ON DELETE CASCADE,
    canonical_product_id  INTEGER REFERENCES canonical_products(id),
    market_id             INTEGER NOT NULL REFERENCES markets(id),
    catalog_id            INTEGER NOT NULL REFERENCES catalogs(id),
    price_tl              FLOAT   NOT NULL,
    original_price_tl     FLOAT,
    discount_pct          FLOAT,
    unit_price_tl         FLOAT,
    valid_from            DATE    NOT NULL,
    valid_until           DATE    NOT NULL,
    created_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id                UUID        PRIMARY KEY,
    email             VARCHAR(255) UNIQUE NOT NULL,
    display_name      VARCHAR(100),
    fcm_token         VARCHAR(500),
    preferred_markets JSONB       DEFAULT '[]',
    kvkk_consent      BOOLEAN     DEFAULT FALSE,
    kvkk_consent_at   TIMESTAMPTZ,
    marketing_consent BOOLEAN     DEFAULT FALSE,
    is_active         BOOLEAN     DEFAULT TRUE,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, email, created_at)
    VALUES (NEW.id, NEW.email, NOW())
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

CREATE TABLE IF NOT EXISTS watchlist (
    id                        SERIAL PRIMARY KEY,
    user_id                   UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    canonical_product_id      INTEGER NOT NULL REFERENCES canonical_products(id),
    price_threshold_tl        FLOAT   CHECK (price_threshold_tl > 0),
    unit_price_threshold_tl   FLOAT   CHECK (unit_price_threshold_tl > 0),
    notify_on_any_discount    BOOLEAN DEFAULT TRUE,
    notify_early              BOOLEAN DEFAULT TRUE,
    is_active                 BOOLEAN DEFAULT TRUE,
    created_at                TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, canonical_product_id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id                    SERIAL PRIMARY KEY,
    user_id               UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    watchlist_id          INTEGER REFERENCES watchlist(id),
    canonical_product_id  INTEGER REFERENCES canonical_products(id),
    market_id             INTEGER REFERENCES markets(id),
    channel               VARCHAR(20) DEFAULT 'push' CHECK (channel IN ('push','email','sms')),
    status                VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','sent','failed','read')),
    title                 VARCHAR(200),
    body                  TEXT,
    price_tl              FLOAT,
    discount_pct          FLOAT,
    fcm_message_id        VARCHAR(200),
    sent_at               TIMESTAMPTZ,
    read_at               TIMESTAMPTZ,
    created_at            TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security
ALTER TABLE users         ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlist     ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE markets            ENABLE ROW LEVEL SECURITY;
ALTER TABLE catalogs           ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_products       ENABLE ROW LEVEL SECURITY;
ALTER TABLE canonical_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_prices     ENABLE ROW LEVEL SECURITY;
ALTER TABLE categories         ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_data"         ON users            FOR ALL    USING (auth.uid() = id);
CREATE POLICY "watchlist_own_data"     ON watchlist        FOR ALL    USING (auth.uid() = user_id);
CREATE POLICY "notifications_own_data" ON notifications    FOR ALL    USING (auth.uid() = user_id);
CREATE POLICY "markets_public_read"    ON markets          FOR SELECT USING (TRUE);
CREATE POLICY "catalogs_public_read"   ON catalogs         FOR SELECT USING (TRUE);
CREATE POLICY "raw_products_read"      ON raw_products     FOR SELECT USING (TRUE);
CREATE POLICY "canonical_read"         ON canonical_products FOR SELECT USING (TRUE);
CREATE POLICY "prices_public_read"     ON product_prices   FOR SELECT USING (TRUE);
CREATE POLICY "categories_public_read" ON categories       FOR SELECT USING (TRUE);

-- Aktif kampanyalar view
CREATE OR REPLACE VIEW active_deals AS
SELECT
    rp.id AS product_id, rp.raw_name AS name, rp.image_url,
    pp.price_tl, pp.original_price_tl, pp.discount_pct, pp.unit_price_tl,
    cp.unit_type, cp.unit_size, cp.normalized_name, cp.brand,
    m.name AS market_name, m.slug AS market_slug, m.logo_url AS market_logo,
    c.valid_from, c.valid_until,
    cat.name AS category_name
FROM raw_products rp
JOIN product_prices pp   ON rp.id = pp.raw_product_id
JOIN markets m           ON pp.market_id = m.id
JOIN catalogs c          ON pp.catalog_id = c.id
LEFT JOIN canonical_products cp ON rp.canonical_product_id = cp.id
LEFT JOIN categories cat        ON cp.category_id = cat.id
WHERE c.status = 'active'
  AND c.valid_from  <= CURRENT_DATE
  AND c.valid_until >= CURRENT_DATE
  AND m.is_active = TRUE
ORDER BY pp.unit_price_tl ASC NULLS LAST;
