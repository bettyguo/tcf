// Client-only providers (Query, theme-attribute sync, locale).
// The locale messages are passed in by the server layout so that the
// initial HTML response is fully translated (no flash of English).

"use client";

import { type ReactNode, useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { useUiStore } from "@/lib/state/ui-store";

interface Props {
  locale: string;
  messages: Record<string, unknown>;
  timeZone?: string;
  children: ReactNode;
}

export function Providers({ locale, messages, timeZone, children }: Props) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      }),
  );

  const theme = useUiStore((s) => s.theme);
  const font = useUiStore((s) => s.font);

  // Mirror theme + font to <html> for CSS to consume.
  useEffect(() => {
    if (typeof document === "undefined") return;
    const html = document.documentElement;
    if (theme === "auto") html.removeAttribute("data-theme");
    else html.setAttribute("data-theme", theme);
    html.setAttribute("data-dyslexic", String(font === "dyslexic"));
  }, [theme, font]);

  return (
    <NextIntlClientProvider locale={locale} messages={messages} timeZone={timeZone}>
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    </NextIntlClientProvider>
  );
}
