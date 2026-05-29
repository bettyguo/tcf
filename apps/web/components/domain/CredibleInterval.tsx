// CredibleInterval — the single supported way to render an NCLC value.
// ADR-025 enforcement. A custom lint rule rejects free-form "NCLC \d+"
// strings outside this component (see eslint/no-bare-nclc.js).
//
// `format="bar"` — visual horizontal bar with mean tick
// `format="inline"` — text form "NCLC 8 (CI 7–9)"
// `format="tuple"` — just "7–9" for tight tables

import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { formatCi, formatNclcMean } from "@/lib/format";
import type { PosteriorEstimate } from "@/lib/types";

type Format = "bar" | "inline" | "tuple";
type Status = "ok" | "weak" | "strong";

interface Props {
  posterior: PosteriorEstimate;
  domain?: [number, number];
  format?: Format;
  status?: Status;
  ariaLabel?: string;
}

const STATUS_FG: Record<Status, string> = {
  ok: "bg-accent",
  weak: "bg-danger",
  strong: "bg-success",
};

export function CredibleInterval({
  posterior,
  domain = [1, 12],
  format = "bar",
  status = "ok",
  ariaLabel,
}: Props): ReactNode {
  const [lo, hi] = domain;
  const span = hi - lo || 1;
  const left = Math.max(0, ((posterior.lower - lo) / span) * 100);
  const right = Math.min(100, ((posterior.upper - lo) / span) * 100);
  const mean = Math.max(0, Math.min(100, ((posterior.mean - lo) / span) * 100));
  const label =
    ariaLabel ??
    `NCLC ${formatNclcMean(posterior.mean)}, credible interval ${formatCi(posterior)}.`;

  if (format === "inline") {
    return (
      <span className="num" aria-label={label}>
        NCLC {formatNclcMean(posterior.mean)} (CI {formatCi(posterior)})
      </span>
    );
  }
  if (format === "tuple") {
    return (
      <span className="num" aria-label={label}>
        {formatCi(posterior)}
      </span>
    );
  }
  return (
    <div className="flex items-center gap-2" role="img" aria-label={label}>
      <span className="num min-w-[3rem] text-sm font-semibold">
        NCLC {formatNclcMean(posterior.mean)}
      </span>
      <span className="relative h-3 w-full max-w-[260px] rounded-full bg-border">
        <span
          className={cn(
            "absolute top-0 h-3 rounded-full opacity-30",
            STATUS_FG[status],
          )}
          style={{ left: `${left}%`, width: `${Math.max(2, right - left)}%` }}
        />
        <span
          className={cn(
            "absolute top-[-2px] h-[16px] w-[2px] rounded-sm",
            STATUS_FG[status],
          )}
          style={{ left: `${mean}%` }}
        />
      </span>
      <span className="num text-xs text-muted">
        ({formatCi(posterior)})
      </span>
    </div>
  );
}
