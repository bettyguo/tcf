import { notFound } from "next/navigation";
import { SkillTrajectory } from "@/components/domain/SkillTrajectory";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { CredibleInterval } from "@/components/domain/CredibleInterval";
import { skills, type Skill, type SkillState } from "@/lib/types";

function fixture(skill: Skill): SkillState {
  return {
    skill,
    target: 9,
    posterior: { mean: 8, lower: 7, upper: 9, nObservations: 60 },
    history: Array.from({ length: 8 }).map((_, i) => ({
      at: new Date(Date.now() - (7 - i) * 7 * 86400000).toISOString(),
      posterior: {
        mean: 6.5 + i * 0.2,
        lower: 5.5 + i * 0.2,
        upper: 7.8 + i * 0.2,
        nObservations: 5 + i * 4,
      },
    })),
  };
}

export default async function SkillPage({
  params,
}: {
  params: Promise<{ skill: string }>;
}) {
  const { skill: raw } = await params;
  const skill = raw.toUpperCase() as Skill;
  if (!skills.includes(skill)) notFound();
  const state = fixture(skill);
  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">{skill}</h1>
        <CredibleInterval posterior={state.posterior} format="inline" />
      </header>
      <Card>
        <CardHeader>
          <CardTitle>Trajectory</CardTitle>
        </CardHeader>
        <SkillTrajectory
          skill={state.skill}
          history={state.history}
          target={state.target}
          width={600}
          height={220}
        />
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Top weak patterns</CardTitle>
        </CardHeader>
        <ul className="list-disc pl-5 text-sm">
          <li>Past tense agreement in subordinate clauses.</li>
          <li>Discourse markers (en effet, par ailleurs) underused.</li>
          <li>Hedging vocabulary at register 2 missing.</li>
        </ul>
      </Card>
    </div>
  );
}
