"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { DrillPlayer } from "@/components/domain/DrillPlayer";
import type { DrillItem } from "@/lib/state/drill-store";
import { Button } from "@/components/ui/Button";
import { useState } from "react";

const FIRST: DrillItem = {
  id: "diag-1",
  kind: "CE_SKIM",
  prompt:
    "Diagnostic Q1 — Read the paragraph (rendered above) and pick the closest paraphrase.",
  options: [
    { id: "a", label: "Quebec implemented a price ceiling." },
    { id: "b", label: "Vacancy rates declined in 2023." },
    { id: "c", label: "Federal lending policy is unchanged." },
    { id: "d", label: "The article is about mortgage rates only." },
  ],
  timeLimitSeconds: 90,
};

export default function DiagnosticPage() {
  const t = useTranslations("onboarding.diagnostic");
  const router = useRouter();
  const [started, setStarted] = useState(false);
  if (!started) {
    return (
      <section>
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <p className="mt-2 text-sm text-muted">{t("intro")}</p>
        <Button className="mt-4" onClick={() => setStarted(true)}>
          Start
        </Button>
      </section>
    );
  }
  return (
    <DrillPlayer
      item={FIRST}
      onSubmit={async () => ({
        rationale: "(Diagnostic continues — fixture skips ahead in this scaffold.)",
      })}
      onNext={() => router.push("/onboarding/plan-preview")}
      onEnd={() => router.push("/onboarding/plan-preview")}
    />
  );
}
