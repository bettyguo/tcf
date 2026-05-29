"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { stubLocales, type Locale } from "@/lib/i18n/config";

export function StubLocaleBanner() {
  const locale = useLocale() as Locale;
  const t = useTranslations();
  const [dismissed, setDismissed] = useState(false);
  if (!stubLocales.has(locale) || dismissed) return null;
  return (
    <div
      role="status"
      className="mb-3 rounded-md border border-warning bg-card px-3 py-2 text-sm"
    >
      <p className="inline">{t("stubBanner")}</p>
      <button
        onClick={() => setDismissed(true)}
        aria-label="Dismiss"
        className="ml-2 underline"
      >
        ✕
      </button>
    </div>
  );
}
