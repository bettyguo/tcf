// Phase 8 i18n config (see phase8_design.md §7).
// EN + FR are first-class; ES/AR/ZH are RTL/LTR-stubbed with English
// fallback (the message catalog inherits keys from en.json).

export const locales = ["en", "fr", "es", "ar", "zh"] as const;
export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = "en";

export const localeLabels: Record<Locale, string> = {
  en: "English",
  fr: "Français",
  es: "Español",
  ar: "العربية",
  zh: "中文",
};

export const rtlLocales: ReadonlySet<Locale> = new Set(["ar"]);

export function isRtl(locale: Locale): boolean {
  return rtlLocales.has(locale);
}

// Locales where the v1 translation is incomplete. UI shows an informational
// banner ("translation incomplete; English shown where missing").
export const stubLocales: ReadonlySet<Locale> = new Set(["es", "ar", "zh"]);
