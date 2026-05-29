// The booking decision page — phase8_design.md §12.3.
// Checklist gates the booking CTA against ADR-045.

import { getTranslations } from "next-intl/server";
import { ReadinessWidget } from "@/components/domain/ReadinessWidget";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { deriveReadiness } from "@/lib/readiness";
import type { SkillState } from "@/lib/types";

function fixture(): SkillState[] {
  return [
    {
      skill: "CO",
      target: 9,
      posterior: { mean: 9, lower: 8, upper: 10, nObservations: 30 },
      history: [],
    },
    {
      skill: "CE",
      target: 9,
      posterior: { mean: 9, lower: 8, upper: 10, nObservations: 30 },
      history: [],
    },
    {
      skill: "EE",
      target: 9,
      posterior: { mean: 8, lower: 7, upper: 9, nObservations: 30 },
      history: [],
    },
    {
      skill: "EO",
      target: 9,
      posterior: { mean: 8.4, lower: 8, upper: 9, nObservations: 30 },
      history: [],
    },
  ];
}

export default async function ReadinessPage() {
  const t = await getTranslations("readiness");
  const skills = fixture();
  const summary = deriveReadiness({
    skills,
    target: 9,
    canonicalMocksCompleted: 1,
    consecutiveGreenMocks: 1,
    probabilityMinAtTarget: 0.72,
  });
  return (
    <div className="space-y-4">
      <ReadinessWidget summary={summary} />
      <Card>
        <CardHeader>
          <CardTitle>{t("checklistTitle")}</CardTitle>
        </CardHeader>
        <ul className="space-y-2 text-sm">
          <li>✅ {t("checklist.diagnostic")}</li>
          <li>✅ {t("checklist.mock1")}</li>
          <li>⬜ {t("checklist.mock2")}</li>
          <li>⬜ {t("checklist.fee")}</li>
          <li>⬜ {t("checklist.id")}</li>
        </ul>
      </Card>
    </div>
  );
}
