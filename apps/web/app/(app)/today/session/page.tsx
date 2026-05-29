// Active drill session. Hosts the DrillPlayer with deterministic fixture
// data; real backing comes from /v1/session/* (Phase 5).

"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { DrillPlayer } from "@/components/domain/DrillPlayer";
import type { DrillItem } from "@/lib/state/drill-store";

const FIXTURE: Record<string, DrillItem> = {
  b1: {
    id: "i-ee-1",
    kind: "EE_TIMED_WRITE",
    prompt:
      "Write 180 mots on the trade-offs of renting vs. buying a home in a Canadian city of your choice.",
    timeLimitSeconds: 25 * 60,
  },
  b3: {
    id: "i-ce-1",
    kind: "CE_SKIM",
    prompt:
      "Skim the passage in 90 seconds, then answer: what is the author's primary argument?",
    options: [
      { id: "a", label: "Housing affordability has improved in Montréal." },
      { id: "b", label: "Federal transfer payments are inadequate." },
      { id: "c", label: "Municipal zoning is the dominant constraint." },
      { id: "d", label: "Rural migration is reversing." },
    ],
    timeLimitSeconds: 5 * 60,
  },
};

export default function SessionPage() {
  const search = useSearchParams();
  const router = useRouter();
  const blockId = search.get("block") ?? "b1";
  const item = FIXTURE[blockId] ?? FIXTURE.b1!;

  async function submit() {
    await new Promise((r) => setTimeout(r, 250));
    return { rationale: "Looks reasonable. See the rationale tab for details." };
  }

  return (
    <DrillPlayer
      item={item}
      onSubmit={submit}
      onNext={() => router.push("/today")}
      onEnd={() => router.push("/today")}
      showRationale
    />
  );
}
