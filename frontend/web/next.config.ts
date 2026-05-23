import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { hostname: '*.migros.com.tr' },
      { hostname: '*.bim.com.tr' },
      { hostname: '*.a101.com.tr' },
      { hostname: '*.sokmarket.com.tr' },
      { hostname: '*.carrefoursa.com' },
    ],
  },
  experimental: {
    serverActions: { allowedOrigins: ['localhost:3000'] },
  },
}

export default nextConfig
