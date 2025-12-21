import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Enable server actions for chat functionality
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
  // Externalize native modules (DuckDB) for server-side rendering
  serverExternalPackages: ['duckdb', 'duckdb-async'],
};

export default nextConfig;
