// MockReport — the 7-section Phase 6 report. Exposes the inflation-
// guard banner (ADR-040) prominently so silent clamping doesn't leak
// credibility.

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { CredibleInterval } from "./CredibleInterval";
import { RubricCard } from "./RubricCard";
import type { MockReportPayload } from "@/lib/types";

interface Props {
  report: MockReportPayload;
  onDrill?: (kind: string, id: string) => void;
}

export function MockReport({ report, onDrill }: Props): ReactNode {
  const t = useTranslations("mockExam.report");
  return (
    <article className="space-y-5">
      {/* 1. Headline */}
      <Card>
        <CardHeader>
          <CardTitle>{t("headline", { min: report.overallNclc })}</CardTitle>
          <Badge tone={report.mode === "canonical" ? "accent" : "warning"}>
            {report.mode === "canonical" ? "🟦 CANONICAL" : "🟧 TRAINING"}
          </Badge>
        </CardHeader>
        <p className="text-sm text-muted">
          Taken {new Date(report.takenAt).toLocaleString()}
        </p>
      </Card>

      {/* 2. Per-skill */}
      <Card>
        <CardHeader>
          <CardTitle>Per-skill</CardTitle>
        </CardHeader>
        <ul className="space-y-3">
          {report.perSkill.map((s) => (
            <li key={s.skill} className="flex items-center justify-between gap-3">
              <span className="font-semibold">{s.skill}</span>
              <CredibleInterval
                posterior={{
                  mean: s.nclc,
                  lower: s.ci[0],
                  upper: s.ci[1],
                  nObservations: 0,
                }}
              />
            </li>
          ))}
        </ul>
      </Card>

      {/* 3. Inflation-guard banner (ADR-040) */}
      {report.inflationClamped.length > 0 && (
        <Card className="border-warning">
          <p className="text-sm">
            ⚠ {t("inflationClamped", { n: report.inflationClamped.length })}
          </p>
          <ul className="mt-2 list-disc pl-5 text-sm text-muted">
            {report.inflationClamped.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </Card>
      )}

      {/* 4. EE span-annotated essay (rendered as HTML by the API) */}
      {report.perSkill
        .filter((s) => s.spanAnnotated)
        .map((s) => (
          <Card key={`anno-${s.skill}`}>
            <CardHeader>
              <CardTitle>{s.skill} — annotated</CardTitle>
            </CardHeader>
            <div
              className="prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: s.spanAnnotated! }}
            />
          </Card>
        ))}

      {/* 5. EO audio + transcript */}
      {report.perSkill
        .filter((s) => s.audioUrl)
        .map((s) => (
          <Card key={`audio-${s.skill}`}>
            <CardHeader>
              <CardTitle>{s.skill} — playback</CardTitle>
            </CardHeader>
            <audio controls src={s.audioUrl} className="w-full">
              <track kind="captions" />
            </audio>
            {s.transcript && (
              <details className="mt-2 text-sm">
                <summary className="cursor-pointer">Transcript</summary>
                <p className="mt-1 whitespace-pre-wrap">{s.transcript}</p>
              </details>
            )}
          </Card>
        ))}

      {/* 6. Rubric breakdowns */}
      {report.perSkill.map(
        (s) =>
          s.rubric &&
          s.rubric.map((r) => (
            <RubricCard
              key={`${s.skill}-${r.task}`}
              rubric={s.skill as "EE" | "EO"}
              task={r.task}
              dimensions={r.dimensions}
              onDrill={onDrill}
            />
          )),
      )}

      {/* 7. Next steps + κ footer */}
      <Card>
        <CardHeader>
          <CardTitle>{t("nextSteps")}</CardTitle>
        </CardHeader>
        <ol className="space-y-2 text-sm">
          {report.nextSteps.map((n) => (
            <li key={n.id} className="flex items-center justify-between gap-2">
              <span>{n.title}</span>
              <button
                onClick={() => onDrill?.(n.drill, n.id)}
                className="min-h-tap rounded-md border border-border px-3 text-xs font-medium"
              >
                Drill →
              </button>
            </li>
          ))}
        </ol>
        <p className="num mt-4 text-xs text-muted">
          {t("kappa", {
            value: report.kappa.toFixed(2),
            date: new Date(report.kappaCalibratedAt).toLocaleDateString(),
          })}
        </p>
      </Card>
    </article>
  );
}
