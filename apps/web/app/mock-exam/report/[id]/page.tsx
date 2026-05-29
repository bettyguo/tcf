"use client";

import { MockReport } from "@/components/domain/MockReport";
import type { MockReportPayload } from "@/lib/types";

const REPORT: MockReportPayload = {
  id: "fixture",
  mode: "training",
  takenAt: new Date().toISOString(),
  overallNclc: 8,
  perSkill: [
    { skill: "CO", nclc: 9, ci: [8, 10] },
    { skill: "CE", nclc: 9, ci: [8, 10] },
    {
      skill: "EE",
      nclc: 8,
      ci: [7, 9],
      rubric: [
        {
          task: 2,
          dimensions: [
            { key: "task", label: "Task completion", score: 4, rationale: "Addresses the prompt." },
            { key: "coh", label: "Coherence", score: 3, rationale: "Some weak connectors." },
            { key: "lex", label: "Lexical range", score: 4, rationale: "MATTR within NCLC 8 band." },
            { key: "gram", label: "Grammar", score: 3, rationale: "Several past-tense agreement errors." },
            { key: "reg", label: "Register", score: 4, rationale: "Soutenu, appropriate." },
            { key: "ca", label: "Canadian context", score: 3, rationale: "Light on Canadian framing.", clamped: true },
          ],
        },
      ],
    },
    {
      skill: "EO",
      nclc: 8,
      ci: [8, 9],
      audioUrl: "/fixtures/eo-sample.wav",
      transcript: "Le logement est un enjeu central dans les villes canadiennes…",
    },
  ],
  inflationClamped: ["EE/Canadian context"],
  nextSteps: [
    { title: "Past-tense agreement drill", drill: "EE_TIMED_WRITE", id: "drill-1" },
    { title: "Canadian-context vocabulary", drill: "CE_SKIM", id: "drill-2" },
    { title: "Shadowing 5 minutes/day", drill: "CO_SHADOWING", id: "drill-3" },
  ],
  kappa: 0.71,
  kappaCalibratedAt: new Date().toISOString(),
};

export default function MockReportPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-6">
      <MockReport report={REPORT} />
    </main>
  );
}
