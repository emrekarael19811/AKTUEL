export interface Market {
  id: number
  name: string
  slug: string
  website_url: string
  logo_url?: string
  catalog_cycle_days: number
  catalog_publish_weekday?: number
  is_active: boolean
}

export interface Catalog {
  id: number
  market_id: number
  market_name: string
  market_slug: string
  valid_from: string
  valid_until: string
  pdf_url?: string
  status: CatalogStatus
  raw_product_count: number
}

export type CatalogStatus =
  | 'pending'
  | 'downloading'
  | 'ocr_processing'
  | 'parsing'
  | 'indexing'
  | 'active'
  | 'expired'
  | 'failed'

export interface Product {
  product_id: number
  name: string
  market_name: string
  market_slug: string
  price_tl?: number
  original_price_tl?: number
  discount_pct?: number
  unit_price_tl?: number
  unit_type?: string
  unit_size?: number
  image_url?: string
  valid_from?: string
  valid_until?: string
  highlight?: Record<string, string[]>
  score?: number
  brand?: string
  category?: string
}

export interface SearchResponse {
  total: number
  products: Product[]
  query: string
}

export interface WatchlistItem {
  id: number
  canonical_product_id: number
  price_threshold_tl?: number
  unit_price_threshold_tl?: number
  notify_on_any_discount: boolean
  notify_early: boolean
  is_active: boolean
}

export interface PriceHistory {
  date: string
  price_tl: number
  unit_price_tl?: number
  market: string
  market_slug: string
}
