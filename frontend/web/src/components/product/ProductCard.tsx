'use client'

import Image from 'next/image'
import { Heart } from 'lucide-react'
import type { Product } from '@/types'

interface ProductCardProps {
  product: Product
  onWatchlistToggle?: (productId: number) => void
  isWatched?: boolean
}

export function ProductCard({ product, onWatchlistToggle, isWatched }: ProductCardProps) {
  const hasDiscount = product.discount_pct && product.discount_pct > 0

  return (
    <div className="relative flex flex-col bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
      {/* İndirim rozeti */}
      {hasDiscount && (
        <span className="absolute top-2 left-2 z-10 bg-red-500 text-white text-xs font-bold px-2 py-1 rounded-full">
          %{Math.round(product.discount_pct!)} İNDİRİM
        </span>
      )}

      {/* Favori butonu */}
      {onWatchlistToggle && (
        <button
          onClick={() => onWatchlistToggle(product.product_id)}
          className="absolute top-2 right-2 z-10 p-1.5 rounded-full bg-white/80 backdrop-blur-sm"
          aria-label="Takip listesine ekle"
        >
          <Heart
            className={`w-4 h-4 ${isWatched ? 'fill-red-500 text-red-500' : 'text-gray-400'}`}
          />
        </button>
      )}

      {/* Ürün görseli */}
      <div className="relative h-40 bg-gray-50">
        {product.image_url ? (
          <Image
            src={product.image_url}
            alt={product.name}
            fill
            className="object-contain p-3"
            sizes="(max-width: 640px) 50vw, 25vw"
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-300 text-4xl">
            🛒
          </div>
        )}
      </div>

      {/* İçerik */}
      <div className="p-3 flex flex-col gap-1 flex-1">
        {/* Market logosu/adı */}
        <span className="text-xs text-gray-400 uppercase tracking-wide font-medium">
          {product.market_name}
        </span>

        {/* Ürün adı */}
        <h3
          className="text-sm font-semibold text-gray-800 line-clamp-2 leading-tight"
          dangerouslySetInnerHTML={{
            __html: product.highlight?.name?.[0] ?? product.name,
          }}
        />

        {/* Fiyat */}
        <div className="mt-auto pt-2">
          <div className="flex items-baseline gap-1.5">
            <span className="text-lg font-bold text-red-600">
              {product.price_tl != null ? formatPrice(product.price_tl) : '—'}
            </span>
            {product.original_price_tl && (
              <span className="text-xs text-gray-400 line-through">
                {formatPrice(product.original_price_tl)}
              </span>
            )}
          </div>

          {/* Birim fiyat */}
          {product.unit_price_tl != null && (
            <p className="text-xs text-gray-500 mt-0.5">
              {formatUnitPrice(product.unit_price_tl, product.unit_type)}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

function formatPrice(tl: number): string {
  return new Intl.NumberFormat('tr-TR', {
    style: 'currency',
    currency: 'TRY',
    minimumFractionDigits: 2,
  }).format(tl)
}

function formatUnitPrice(tl: number, unitType?: string): string {
  const unit = unitType === 'g' || unitType === 'ml'
    ? `100${unitType}`
    : unitType ?? 'adet'
  return `${formatPrice(tl)} / ${unit}`
}
