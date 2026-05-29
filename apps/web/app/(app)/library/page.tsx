import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";

const SECTIONS = [
  { key: "grammar", href: "/library/grammar" as const },
  { key: "vocab", href: "/library/vocab" as const },
  { key: "writing", href: "/library/writing" as const },
  { key: "speaking", href: "/library/speaking" as const },
  { key: "culture", href: "/library/culture" as const },
];

export default async function LibraryPage() {
  const t = await getTranslations("library");
  return (
    <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
      {SECTIONS.map((s) => (
        <li key={s.key}>
          <Link href={s.href} className="block">
            <Card>
              <CardHeader>
                <CardTitle>{t(s.key as "grammar" | "vocab" | "writing" | "speaking" | "culture")}</CardTitle>
              </CardHeader>
              <p className="text-sm text-muted">
                Browse, then return to today's drills.
              </p>
            </Card>
          </Link>
        </li>
      ))}
    </ul>
  );
}
