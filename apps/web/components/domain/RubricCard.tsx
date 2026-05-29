// RubricCard — one EE/EO task's dimensions, with clamp visibility
// (ADR-040) and drill links closing the loop into Phase 5.

import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { RubricDimension } from "@/lib/types";

interface Props {
  rubric: "EE" | "EO";
  task: 1 | 2 | 3;
  dimensions: RubricDimension[];
  onDrill?: (kind: string, id: string) => void;
}

export function RubricCard({
  rubric,
  task,
  dimensions,
  onDrill,
}: Props): ReactNode {
  const clamps = dimensions.filter((d) => d.clamped).length;
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {rubric} — Task {task}
        </CardTitle>
        {clamps > 0 && (
          <Badge tone="warning" aria-label={`${clamps} clamped dimension(s)`}>
            ⚠ {clamps} clamped
          </Badge>
        )}
      </CardHeader>
      <ul className="divide-y divide-border">
        {dimensions.map((d) => (
          <li key={d.key} className="grid grid-cols-[6rem_1fr_auto] gap-3 py-3">
            <span className="num text-sm font-semibold">
              {d.score}/5{d.clamped && <span aria-hidden> ⚠</span>}
            </span>
            <div>
              <p className={cn("text-sm font-medium", d.clamped && "text-warning")}>
                {d.label}
              </p>
              <p className="mt-1 text-sm text-muted">{d.rationale}</p>
            </div>
            {d.drillLink && onDrill && (
              <button
                onClick={() => onDrill(d.drillLink!.kind, d.drillLink!.id)}
                className="min-h-tap self-center rounded-md border border-border px-3 text-xs font-medium"
              >
                Drill →
              </button>
            )}
          </li>
        ))}
      </ul>
    </Card>
  );
}
