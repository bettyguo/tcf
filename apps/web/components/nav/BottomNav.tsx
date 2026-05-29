// Three tabs only — phase8_design.md §2.3. Settings is the top-right
// cog, not a tab. Active state is shown by underline + 600-weight,
// never by color alone.

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/cn";

interface Tab {
  href: "/today" | "/insights" | "/library";
  key: "today" | "insights" | "library";
}

const TABS: Tab[] = [
  { href: "/today", key: "today" },
  { href: "/insights", key: "insights" },
  { href: "/library", key: "library" },
];

export function BottomNav() {
  const path = usePathname();
  const t = useTranslations("nav");
  return (
    <nav
      aria-label="Primary"
      className={cn(
        "fixed inset-x-0 bottom-0 z-20 border-t border-border bg-card",
        "pb-[env(safe-area-inset-bottom)]",
        "lg:static lg:border-0 lg:bg-transparent lg:pb-0",
      )}
    >
      <ul className="grid grid-cols-3 gap-1 lg:flex lg:flex-col lg:gap-2">
        {TABS.map((tab) => {
          const active = path?.startsWith(tab.href);
          return (
            <li key={tab.href}>
              <Link
                href={tab.href}
                className={cn(
                  "flex min-h-tap items-center justify-center gap-1 text-sm",
                  active
                    ? "font-semibold underline underline-offset-4"
                    : "font-medium text-muted",
                )}
                aria-current={active ? "page" : undefined}
              >
                {t(tab.key)}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
