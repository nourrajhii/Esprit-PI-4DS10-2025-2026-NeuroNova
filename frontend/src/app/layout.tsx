import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'EstateMind — Plateforme Immobilière Intelligente Tunisie',
  description: 'Recherchez, analysez et investissez dans l\'immobilier tunisien grâce à l\'intelligence artificielle.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Work+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css" />
        <link rel="stylesheet" href="/property-template.css" />
      </head>
      <body className="min-h-screen bg-white font-sans">
        {children}
      </body>
    </html>
  )
}
