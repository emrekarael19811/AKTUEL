import { Suspense } from 'react'
import { SearchBar } from '@/components/product/SearchBar'
import { ProductCard } from '@/components/product/ProductCard'
import { searchProducts } from '@/lib/api'
import type { SearchResponse } from '@/types'

interface SearchPageProps {
  searchParams: { q?: string; markets?: string; page?: string }
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const query = searchParams.q?.trim() ?? ''
  const page = Number(searchParams.page ?? 1)
  const markets = searchParams.markets

  let result: SearchResponse = { total: 0, products: [], query }

  if (query.length >= 2) {
    result = await searchProducts({ q: query, markets, page, size: 24 }).catch(() => result)
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-100 px-4 py-4 sticky top-0 z-30">
        <div className="max-w-3xl mx-auto">
          <SearchBar initialQuery={query} />
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-6">
        {query.length >= 2 ? (
          <>
            <p className="text-sm text-gray-500 mb-5">
              <span className="font-semibold text-gray-800">&ldquo;{query}&rdquo;</span> için{' '}
              <span className="font-semibold text-gray-800">{result.total}</span> sonuç
              — birim fiyata göre sıralı
            </p>

            {result.products.length === 0 ? (
              <div className="text-center py-20 text-gray-400">
                <p className="text-5xl mb-4">🔍</p>
                <p className="text-lg font-medium">Ürün bulunamadı</p>
                <p className="text-sm mt-1">Farklı bir arama terimi deneyin</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
                {result.products.map((product) => (
                  <ProductCard key={product.product_id} product={product} />
                ))}
              </div>
            )}

            {/* Pagination */}
            {result.total > 24 && (
              <div className="flex justify-center gap-2 mt-8">
                {page > 1 && (
                  <a
                    href={`/search?q=${encodeURIComponent(query)}&page=${page - 1}`}
                    className="px-4 py-2 rounded-lg bg-white border border-gray-200 text-sm font-medium hover:bg-gray-50"
                  >
                    ← Önceki
                  </a>
                )}
                {result.total > page * 24 && (
                  <a
                    href={`/search?q=${encodeURIComponent(query)}&page=${page + 1}`}
                    className="px-4 py-2 rounded-lg bg-red-500 text-white text-sm font-medium hover:bg-red-600"
                  >
                    Sonraki →
                  </a>
                )}
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-20 text-gray-400">
            <p className="text-5xl mb-4">🛒</p>
            <p className="text-lg font-medium">Bir ürün adı girin</p>
            <p className="text-sm mt-1">En az 2 karakter yazın</p>
          </div>
        )}
      </div>
    </main>
  )
}
