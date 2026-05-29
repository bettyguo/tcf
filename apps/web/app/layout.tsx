// Root layout. Sets html lang + dir from the resolved locale, mounts
// the providers, and emits the Phase 8 calm-by-default visual chrome.

import type { Metadata } from "next";
import type { ReactNode } from "react";
import { getLocale, getMessages, getTimeZone } from "next-intl/server";
import { Providers } from "./providers";
import { isRtl, type Locale } from "@/lib/i18n/config";
import "./globals.css";

export const metadata: Metadata = {
  title: "tcf-accel",
  description:
    "Evidence-based, exam-aligned French training for TCF Canada (B1 → NCLC 9+).",
};

export default async function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  const locale = (await getLocale()) as Locale;
  const messages = await getMessages();
  const timeZone = await getTimeZone();
  return (
    <html lang={locale} dir={isRtl(locale) ? "rtl" : "ltr"}>
      <body className="min-h-screen bg-bg text-fg antialiased">
        <Providers
          locale={locale}
          messages={messages as Record<string, unknown>}
          timeZone={timeZone}
        >
          {children}
        </Providers>
      </body>
    </html>
  );
}
