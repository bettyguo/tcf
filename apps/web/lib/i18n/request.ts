// next-intl request-config entry point (wired by next-intl plugin in
// next.config.mjs). Resolves the locale from the cookie set by the
// edge middleware in app/middleware.ts, falling back to the default.

import { getRequestConfig } from "next-intl/server";
import { cookies } from "next/headers";
import { defaultLocale, locales, type Locale } from "./config";

const COOKIE_NAME = "tcf_locale";

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const raw = cookieStore.get(COOKIE_NAME)?.value;
  const locale: Locale =
    raw && (locales as readonly string[]).includes(raw)
      ? (raw as Locale)
      : defaultLocale;

  const primary = (await import(`@/messages/${locale}.json`)).default as Record<
    string,
    unknown
  >;
  // Stubbed locales fall back to English for missing keys.
  const fallback =
    locale === defaultLocale
      ? {}
      : ((await import(`@/messages/${defaultLocale}.json`)).default as Record<
          string,
          unknown
        >);

  return {
    locale,
    messages: { ...fallback, ...primary },
  };
});
