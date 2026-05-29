// Insights overview: ReadinessWidget + per-skill trajectory grid.

import { getTranslations } from "next-intl/server";
import { ReadinessWidget } from "@/components/domain/ReadinessWidget";
import { SkillTrajectory } from "@/components/domain/SkillTrajectory";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { deriveReadiness } from "@/lib/readiness";
import type { Skill, SkillState } from "@/lib/types";

function fixtureSkills(): SkillState[] {
  const make = (skill: Skill, mean: number, lo: number, hi: number): SkillState => ({
    skill,
    target: 9,
    posterior: { mean, lower: lo, upper: hi, nObservations: 60 },
    history: Array.from({ length: 8 }).map((_, i) => ({
      at: new Date(Date.now() - (7 - i) * 7 * 86400000).toISOString(),
      posterior: {
        mean: Math.max(1, mean - (7 - i) * 0.15),
        lower: Math.max(1, lo - (7 - i) * 0.12),
        upper: Math.min(12, hi - (7 - i) * 0.12),
        nObservations: 5 + i * 4,
      },
    })),
  });
  return [
    make("CO", 9, 8, 10),
    make("CE", 9, 8, 10),
    make("EE", 8, 7, 9),
    make("EO", 8.4, 8, 9),
  ];
}

export default async function InsightsPage() {
  const t = await getTranslations("insights");
  const skills = fixtureSkills();
  const summary = deriveReadiness({
    skills,
    target: 9,
    canonicalMocksCompleted: 1,
    consecutiveGreenMocks: 0,
    probabilityMinAtTarget: 0.62,
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>

      <ReadinessWidget summary={summary} />

      <Card>
        <CardHeader>
          <CardTitle>{t("perSkillTrajectory")}</CardTitle>
        </CardHeader>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {skills.map((s) => (
            <SkillTrajectory
              key={s.skill}
              skill={s.skill}
              history={s.history}
              target={s.target}
            />
          ))}
        </div>
      </Card>
    </div>
  );
}
