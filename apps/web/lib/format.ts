// Numeric / CI formatters. All NCLC values are rendered through these
// helpers (see ADR-025: point estimates without CIs are forbidden, and
// the custom ESLint rule defers to <CredibleInterval inline /> for
// free-form copy).

import type { Nclc, PosteriorEstimate } from "./types";

/** Round to one decimal except integers, which render bare. */
export function formatNclcMean(value: Nclc): string {
  if (Math.abs(value - Math.round(value)) < 0.05) {
    return String(Math.round(value));
  }
  return value.toFixed(1);
}

export function formatCi(
  posterior: PosteriorEstimate,
  opts: { dash?: string } = {},
): string {
  const dash = opts.dash ?? "–";
  return `${formatNclcMean(posterior.lower)}${dash}${formatNclcMean(
    posterior.upper,
  )}`;
}

export function formatNclcWithCi(posterior: PosteriorEstimate): string {
  return `NCLC ${formatNclcMean(posterior.mean)} (CI ${formatCi(posterior)})`;
}

export function formatProbability(p: number): string {
  return p.toFixed(2);
}

export function formatMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}
