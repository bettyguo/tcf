// ReadinessWidget — the highest-stakes UI in the product. Renders the
// state computed by `lib/readiness.ts`. ADR-045: never shows green
// without ≥2 consecutive canonical-mode mocks at green (the readiness
// derivation already enforces this; the widget never overrides it).
//
// No celebratory animation on green (phase8_think.md §6).

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/cn";
import { formatProbability } from "@/lib/format";
import type { ReadinessLight, ReadinessSummary } from "@/lib/types";
import { CredibleInterval } from "./CredibleInterval";

interface Props {
  summary: ReadinessSummary;
  onBookExam?: () => void;
  onSeePriorities?: () => void;
}

const LIGHT_CLASS: Record<ReadinessLight, string> = {
  white: "bg-border text-fg",
  red: "bg-danger text-white",
  amber: "bg-warning text-fg",
  green: "bg-success text-white",
};

// Redundant symbols so color-deficient users get the same signal
// (phase8_design.md §8.3).
const LIGHT_SYMBOL: Record<ReadinessLight, string> = {
  white: "◯",
  red: "■",
  amber: "▲",
  green: "●",
};

export function ReadinessWidget({
  summary,
  onBookExam,
  onSeePriorities,
}: Props): ReactNode {
  const t = useTranslations("insights");
  const { state, light, probability, bottleneck, bottleneckPosterior, target } =
    summary;
  const ready = state === "READY";

  return (
    <section
      className="rounded-lg border border-border bg-card p-5 shadow-elev-1"
      aria-labelledby="readiness-title"
    >
      <header className="flex items-center justify-between gap-3">
        <h2 id="readiness-title" className="text-lg font-semibold">
          {t("readinessTitle")}
        </h2>
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm font-medium",
            LIGHT_CLASS[light],
          )}
          aria-label={t(`states.${state}`)}
        >
          <span aria-hidden="true">{LIGHT_SYMBOL[light]}</span>
          <span>{t(`states.${state}`)}</span>
        </span>
      </header>

      <div className="mt-4 space-y-3">
        {state !== "INSUFFICIENT_DATA" && (
          <>
            <p className="text-sm text-muted">
              {t("bottleneck")}: <span className="font-semibold">{bottleneck}</span>
            </p>
            <CredibleInterval
              posterior={bottleneckPosterior}
              status={
                bottleneckPosterior.mean >= target
                  ? "strong"
                  : bottleneckPosterior.mean < target - 1
                    ? "weak"
                    : "ok"
              }
            />
            <p className="num text-sm">
              {t("target", { value: target })} ·{" "}
              {t("probability", { p: formatProbability(probability) })}
            </p>
          </>
        )}

        <div>
          <p className="text-sm font-medium">{t("recommendation")}</p>
          <p className="mt-1 text-sm text-fg">
            {t(`recommendations.${state}`)}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 pt-1">
          {/* Booking CTA hidden in red/white per evaluate.md anti-criteria. */}
          {ready && onBookExam && (
            <button
              onClick={onBookExam}
              className="min-h-tap rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white"
              data-testid="book-exam-cta"
            >
              Book your exam
            </button>
          )}
          {/* Always provide a next action regardless of state. */}
          {onSeePriorities && (
            <button
              onClick={onSeePriorities}
              className="min-h-tap rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-fg"
            >
              See your priority drills
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
