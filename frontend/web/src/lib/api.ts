import type {
  Market, Catalog, Product, SearchResponse, WatchlistItem, PriceHistory,
} from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function fetchApi<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_BASE}${path}`
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    next: { revalidate: 300 }, // 5 dakika Next.js cache
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail ?? `API hatası: ${res.status}`)
  }

  return res.json() as Promise<T>
}

// --- Markets ---
export const getMarkets = (activeOnly = true) =>
  fetchApi<Market[]>(`/api/v1/markets/?active_only=${activeOnly}`)

export const getMarket = (slug: string) =>
  fetchApi<Market>(`/api/v1/markets/${slug}`)

// --- Catalogs ---
export const getCatalogs = (marketSlug?: string) =>
  fetchApi<Catalog[]>(
    `/api/v1/catalogs/${marketSlug ? `?market_slug=${marketSlug}` : ''}`,
  )

// --- Search ---
export interface SearchParams {
  q: string
  markets?: string
  category?: string
  maxPrice?: number
  minDiscount?: number
  page?: number
  size?: number
}

export const searchProducts = (params: SearchParams) => {
  const sp = new URLSearchParams({ q: params.q })
  if (params.markets) sp.set('markets', params.markets)
  if (params.category) sp.set('category', params.category)
  if (params.maxPrice != null) sp.set('max_price', String(params.maxPrice))
  if (params.minDiscount != null) sp.set('min_discount', String(params.minDiscount))
  if (params.page) sp.set('page', String(params.page))
  if (params.size) sp.set('size', String(params.size))
  return fetchApi<SearchResponse>(`/api/v1/search/?${sp.toString()}`)
}

export const getSuggest = (q: string) =>
  fetchApi<string[]>(`/api/v1/search/suggest?q=${encodeURIComponent(q)}`)

// --- Products ---
export const getProducts = (marketSlug?: string, catalogId?: number) => {
  const sp = new URLSearchParams()
  if (marketSlug) sp.set('market_slug', marketSlug)
  if (catalogId) sp.set('catalog_id', String(catalogId))
  return fetchApi<Product[]>(`/api/v1/products/?${sp.toString()}`)
}

export const getPriceHistory = (productId: number, days = 90) =>
  fetchApi<PriceHistory[]>(`/api/v1/products/${productId}/price-history?days=${days}`)

// --- Watchlist ---
export const getWatchlist = (token: string) =>
  fetchApi<WatchlistItem[]>('/api/v1/watchlist/', {
    headers: { Authorization: `Bearer ${token}` },
  })

export const addToWatchlist = (
  payload: {
    canonical_product_id: number
    price_threshold_tl?: number
    notify_on_any_discount?: boolean
  },
  token: string,
) =>
  fetchApi<WatchlistItem>('/api/v1/watchlist/', {
    method: 'POST',
    body: JSON.stringify(payload),
    headers: { Authorization: `Bearer ${token}` },
  })

export const removeFromWatchlist = (itemId: number, token: string) =>
  fetchApi<void>(`/api/v1/watchlist/${itemId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
