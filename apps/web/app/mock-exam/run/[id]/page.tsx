"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { DrillPlayer } from "@/components/domain/DrillPlayer";
import type { DrillItem } from "@/lib/state/drill-store";

const ITEM: DrillItem = {
  id: "mock-1",
  kind: "CE_SKIM",
  prompt:
    "(Mock exam fixture) — read the passage and select the closest paraphrase.",
  options: [
    { id: "a", label: "Federal transfer payments need reform." },
    { id: "b", label: "Municipal zoning is the dominant constraint." },
    { id: "c", label: "Population growth has slowed nationally." },
    { id: "d", label: "Climate policy supersedes housing policy." },
  ],
  timeLimitSeconds: 6 * 60,
};

export default function MockRunner() {
  const search = useSearchParams();
  const router = useRouter();
  const canonical = search.get("mode") === "canonical";
  return (
    <main className="mx-auto max-w-xl px-4 py-6">
      <div className="mb-3 flex items-center justify-between text-xs uppercase tracking-wider">
        <span>{canonical ? "CANONICAL" : "TRAINING"}</span>
        <span>tcf-accel mock</span>
      </div>
      <DrillPlayer
        item={ITEM}
        onSubmit={async () => ({
          rationale: canonical
            ? ""
            : "B — municipal zoning is named as the binding constraint in paragraph 3.",
        })}
        showRationale={!canonical}
        showTranscript={!canonical}
        onEnd={() => router.push("/today")}
        onNext={() => router.push(`/mock-exam/report/new`)}
      />
    </main>
  );
}
