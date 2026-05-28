/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: {
    typedRoutes: true,
  },
  // Phase 8 elaborates: i18n, headers, redirects, image domains, etc.
};

export default nextConfig;
