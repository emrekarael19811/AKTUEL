import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: {
    default: 'AKTÜEL – Süpermarket İndirim Takibi',
    template: '%s | AKTÜEL',
  },
  description: 'BİM, A101, Migros, ŞOK ve CarrefourSA aktüel indirim kataloglarını karşılaştır.',
  keywords: ['indirim', 'aktüel', 'süpermarket', 'katalog', 'bim', 'a101', 'migros'],
  openGraph: {
    title: 'AKTÜEL – Süpermarket İndirim Takibi',
    description: 'Tüm market indirimlerini tek yerden karşılaştır',
    locale: 'tr_TR',
    type: 'website',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body className={`${inter.className} antialiased`}>
        <nav className="bg-white border-b border-gray-100 px-4 py-3 flex items-center justify-between sticky top-0 z-40 shadow-sm">
          <a href="/" className="text-xl font-extrabold text-red-600 tracking-tight">
            AKTÜEL
          </a>
          <div className="flex items-center gap-4 text-sm font-medium text-gray-600">
            <a href="/search" className="hover:text-red-600 transition-colors">Ara</a>
            <a href="/markets" className="hover:text-red-600 transition-colors">Marketler</a>
            <a href="/watchlist" className="hover:text-red-600 transition-colors">Takip</a>
          </div>
        </nav>
        {children}
        <footer className="bg-gray-800 text-gray-400 text-xs text-center py-6 mt-16">
          <p>© {new Date().getFullYear()} AKTÜEL. Tüm hakları saklıdır.</p>
          <p className="mt-1">KVKK kapsamında kişisel verilerinizi koruyoruz.</p>
        </footer>
      </body>
    </html>
  )
}
