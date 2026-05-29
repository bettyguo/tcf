"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { TodayPayload } from "@/lib/types";

export function TodayBlocks({ today }: { today: TodayPayload }) {
  const t = useTranslations("today");
  if (today.blocks.length === 0) {
    return <p className="text-sm text-muted">{t("noBlocks")}</p>;
  }
  return (
    <ol className="space-y-3" aria-label="Today's drill blocks">
      {today.blocks.map((b) => (
        <li key={b.id}>
          <Card>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="num text-xs text-muted">
                  Block {b.index} • {t("block.minutes", { count: b.minutes })} •{" "}
                  {b.skill}
                  {b.priority && (
                    <Badge tone="accent" className="ml-2">
                      {t("priorityTag")}
                    </Badge>
                  )}
                </p>
                <p className="mt-1 text-base font-medium">{b.title}</p>
                {b.subtitle && (
                  <p className="text-sm text-muted">{b.subtitle}</p>
                )}
              </div>
              <Link
                href={{
                  pathname: "/today/session",
                  query: { block: b.id },
                }}
                className="min-h-tap rounded-md bg-accent px-4 py-2 text-sm font-medium text-white"
              >
                {t("block.start")}
              </Link>
            </div>
          </Card>
        </li>
      ))}
    </ol>
  );
}
