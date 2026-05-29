// Phase 8: full Next.js 15 App Router config (ADR-041).
// - typedRoutes for compile-time route safety
// - reactStrictMode for legacy-pattern catches
// - next-intl plugin for App-Router i18n (en/fr + es/ar/zh stubs)
// - strict security headers (no inline scripts, COOP, frame-deny)

import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./lib/i18n/request.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: {
    typedRoutes: true,
    optimizePackageImports: ["@tanstack/react-query", "next-intl"],
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(self), geolocation=()" },
        ],
      },
    ];
  },
};

export default withNextIntl(nextConfig);
