// SkillTrajectory — posterior history + CI shading + target line.
// SVG-rendered (no chart library) for bundle parsimony and a11y.
// Sparkline mode (width <= 200) suppresses axes and labels for
// dashboard embed.

import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { formatNclcMean } from "@/lib/format";
import type { Skill, SkillSnapshot, PosteriorEstimate } from "@/lib/types";
import { CredibleInterval } from "./CredibleInterval";

interface Props {
  skill: Skill;
  history: SkillSnapshot[];
  target: number;
  width?: number;
  height?: number;
  domain?: [number, number];
  className?: string;
}

export function SkillTrajectory({
  skill,
  history,
  target,
  width = 480,
  height = 140,
  domain = [1, 12],
  className,
}: Props): ReactNode {
  const sparkline = width <= 200;
  const padding = sparkline ? 4 : 24;
  const innerW = width - padding * 2;
  const innerH = height - padding * 2;
  const [lo, hi] = domain;

  const xFor = (i: number) =>
    history.length <= 1
      ? padding + innerW / 2
      : padding + (i / (history.length - 1)) * innerW;
  const yFor = (v: number) =>
    padding + innerH - ((v - lo) / (hi - lo)) * innerH;

  const meanPath = history
    .map((h, i) => `${i === 0 ? "M" : "L"} ${xFor(i)} ${yFor(h.posterior.mean)}`)
    .join(" ");

  const lower = history.map((h, i) => `${xFor(i)},${yFor(h.posterior.lower)}`);
  const upper = history
    .slice()
    .reverse()
    .map((h, i) => {
      const idx = history.length - 1 - i;
      return `${xFor(idx)},${yFor(h.posterior.upper)}`;
    });
  const bandPath = `M ${lower.join(" L ")} L ${upper.join(" L ")} Z`;

  const last: PosteriorEstimate | undefined =
    history[history.length - 1]?.posterior;

  return (
    <figure className={cn("flex flex-col gap-2", className)}>
      <svg
        role="img"
        aria-label={`${skill} trajectory; latest posterior ${
          last ? `NCLC ${formatNclcMean(last.mean)}` : "no data"
        }; target NCLC ${target}.`}
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        height={height}
      >
        <title>{skill} trajectory</title>
        <desc>
          Posterior mean with 95% credible interval shading and a horizontal
          target line.
        </desc>
        {/* Target line */}
        <line
          x1={padding}
          x2={width - padding}
          y1={yFor(target)}
          y2={yFor(target)}
          stroke="var(--color-muted)"
          strokeDasharray="4 4"
          strokeWidth={1}
        />
        {/* CI band */}
        {history.length > 0 && (
          <path d={bandPath} fill="var(--color-accent)" opacity={0.15} />
        )}
        {/* Mean line */}
        <path
          d={meanPath}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth={2}
        />
        {!sparkline && (
          <>
            <text
              x={padding}
              y={padding - 6}
              fontSize={10}
              fill="var(--color-muted)"
            >
              NCLC {hi}
            </text>
            <text
              x={padding}
              y={height - 4}
              fontSize={10}
              fill="var(--color-muted)"
            >
              NCLC {lo}
            </text>
          </>
        )}
      </svg>
      {!sparkline && last && (
        <figcaption className="flex items-center justify-between text-sm">
          <span className="font-semibold">{skill}</span>
          <CredibleInterval posterior={last} format="inline" />
        </figcaption>
      )}
    </figure>
  );
}
