import { Suspense } from 'react'
import { SearchBar } from '@/components/product/SearchBar'
import { getMarkets, getCatalogs } from '@/lib/api'
import type { Market, Catalog } from '@/types'
import Link from 'next/link'
import Image from 'next/image'

const MARKET_COLORS: Record<string, string> = {
  migros: 'bg-orange-500',
  bim: 'bg-yellow-500',
  a101: 'bg-red-500',
  sok: 'bg-purple-600',
  carrefoursa: 'bg-blue-600',
}

export default async function HomePage() {
  const [markets, catalogs] = await Promise.all([
    getMarkets().catch(() => [] as Market[]),
    getCatalogs().catch(() => [] as Catalog[]),
  ])

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Hero */}
      <section className="bg-gradient-to-br from-red-600 to-red-800 text-white py-16 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <h1 className="text-4xl font-extrabold mb-3 tracking-tight">
            AKTÜEL
          </h1>
          <p className="text-red-100 text-lg mb-8">
            Tüm süpermarket indirimlerini tek yerden karşılaştır
          </p>
          <SearchBar autoFocus placeholder="Ne arıyorsunuz? (süt, deterjan, yoğurt...)" />
        </div>
      </section>

      {/* Marketler */}
      <section className="max-w-5xl mx-auto px-4 py-10">
        <h2 className="text-xl font-bold text-gray-800 mb-5">Marketler</h2>
        <div className="grid grid-cols-3 sm:grid-cols-5 gap-3">
          {markets.map((market) => (
            <Link
              key={market.slug}
              href={`/markets/${market.slug}`}
              className="flex flex-col items-center gap-2 p-4 bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow"
            >
              <div
                className={`w-12 h-12 rounded-xl ${MARKET_COLORS[market.slug] ?? 'bg-gray-400'} flex items-center justify-center text-white text-xl font-bold`}
              >
                {market.name[0]}
              </div>
              <span className="text-xs font-medium text-gray-700 text-center">
                {market.name}
              </span>
            </Link>
          ))}
        </div>
      </section>

      {/* Aktif Kataloglar */}
      {catalogs.length > 0 && (
        <section className="max-w-5xl mx-auto px-4 pb-16">
          <h2 className="text-xl font-bold text-gray-800 mb-5">
            Bu Hafta&apos;nın Katalogları
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {catalogs.map((catalog) => (
              <Link
                key={catalog.id}
                href={`/markets/${catalog.market_slug}`}
                className="flex items-center gap-4 p-4 bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow"
              >
                <div
                  className={`w-12 h-12 rounded-xl ${MARKET_COLORS[catalog.market_slug] ?? 'bg-gray-400'} flex items-center justify-center text-white text-xl font-bold shrink-0`}
                >
                  {catalog.market_name[0]}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-gray-800 truncate">
                    {catalog.market_name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {formatDate(catalog.valid_from)} – {formatDate(catalog.valid_until)}
                  </p>
                  <p className="text-xs text-red-500 font-medium">
                    {catalog.raw_product_count} ürün
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}
    </main>
  )
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('tr-TR', {
    day: 'numeric',
    month: 'long',
  })
}
