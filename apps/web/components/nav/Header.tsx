"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

export function Header() {
  const t = useTranslations("app");
  return (
    <header className="flex items-center justify-between border-b border-border px-4 py-3">
      <Link href="/today" className="font-semibold">
        {t("title")}
      </Link>
      <Link
        href="/settings/accessibility"
        aria-label="Settings"
        className="min-h-tap min-w-tap inline-flex items-center justify-center rounded-md text-sm"
      >
        ⚙
      </Link>
    </header>
  );
}
