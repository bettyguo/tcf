import type { ReactNode } from "react";
import Link from "next/link";

const TABS = [
  { href: "/settings/account" as const, label: "Account" },
  { href: "/settings/privacy" as const, label: "Privacy" },
  { href: "/settings/accessibility" as const, label: "Accessibility" },
  { href: "/settings/notifications" as const, label: "Notifications" },
  { href: "/settings/api-keys" as const, label: "API keys" },
];

export default function SettingsLayout({ children }: { children: ReactNode }) {
  return (
    <div className="space-y-4">
      <nav aria-label="Settings" className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <Link
            key={t.href}
            href={t.href}
            className="min-h-tap rounded-md border border-border bg-card px-3 py-2 text-sm"
          >
            {t.label}
          </Link>
        ))}
      </nav>
      {children}
    </div>
  );
}
