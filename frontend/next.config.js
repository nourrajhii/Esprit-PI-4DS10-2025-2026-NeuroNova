/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_ORCHESTRATOR_URL: process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8000',
  },
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: '**.menzili.com' },
      { protocol: 'https', hostname: '**.mubawab.tn' },
      { protocol: 'https', hostname: '**.tunisian-properties.com' },
      { protocol: 'https', hostname: '**.tayara.tn' },
      { protocol: 'https', hostname: '**.immobilier.com.tn' },
      { protocol: 'http',  hostname: '**' },
      { protocol: 'https', hostname: '**' },
    ],
  },
}

module.exports = nextConfig
