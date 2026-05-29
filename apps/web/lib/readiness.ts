// Readiness state machine — the single source of truth that gates
// what the <ReadinessWidget /> shows. Enforces ADR-045 (no green
// without ≥ 2 consecutive canonical-mode mocks at green) and
// ADR-025 (CI required, never a point estimate).
//
// Pure function so the unit test owns the truth table without a
// render.

import type {
  Nclc,
  PosteriorEstimate,
  ReadinessLight,
  ReadinessState,
  ReadinessSummary,
  Skill,
  SkillState,
} from "./types";

const LIGHT_FOR_STATE: Record<ReadinessState, ReadinessLight> = {
  INSUFFICIENT_DATA: "white",
  NOT_READY: "red",
  BORDERLINE: "amber",
  READY_ONE_MOCK: "amber", // ADR-045: floor to amber until 2nd green mock
  READY: "green",
  REGRESSED: "red",
};

export interface ReadinessInputs {
  skills: SkillState[];
  target: Nclc;
  /** Canonical-mode mocks completed (per ADR-032 / ADR-045). */
  canonicalMocksCompleted: number;
  /** Number of consecutive canonical mocks ending at green. */
  consecutiveGreenMocks: number;
  /** Most recent canonical mock regressed below target after a previous green. */
  regressed?: boolean;
  /** P(min skill ≥ target) computed by the planner. */
  probabilityMinAtTarget: number;
}

export function deriveReadiness(inputs: ReadinessInputs): ReadinessSummary {
  if (inputs.canonicalMocksCompleted === 0 || inputs.skills.length < 4) {
    return summarize("INSUFFICIENT_DATA", inputs);
  }
  if (inputs.regressed) {
    return summarize("REGRESSED", inputs);
  }

  const bottleneck = pickBottleneck(inputs.skills);
  const mean = bottleneck.posterior.mean;
  const p = inputs.probabilityMinAtTarget;

  if (inputs.consecutiveGreenMocks >= 2 && p >= 0.85) {
    return summarize("READY", inputs, bottleneck);
  }
  if (inputs.consecutiveGreenMocks === 1) {
    return summarize("READY_ONE_MOCK", inputs, bottleneck);
  }
  if (p >= 0.5 || Math.abs(mean - inputs.target) <= 1) {
    return summarize("BORDERLINE", inputs, bottleneck);
  }
  return summarize("NOT_READY", inputs, bottleneck);
}

function pickBottleneck(skills: SkillState[]): SkillState {
  return skills.reduce((min, s) =>
    s.posterior.mean < min.posterior.mean ? s : min,
  );
}

function summarize(
  state: ReadinessState,
  inputs: ReadinessInputs,
  bottleneck?: SkillState,
): ReadinessSummary {
  const fallback: SkillState = {
    skill: "EE",
    target: inputs.target,
    posterior: emptyPosterior(),
    history: [],
  };
  const b = bottleneck ?? inputs.skills[0] ?? fallback;
  return {
    state,
    light: LIGHT_FOR_STATE[state],
    probability: inputs.probabilityMinAtTarget,
    bottleneck: b.skill,
    bottleneckPosterior: b.posterior,
    target: inputs.target,
    consecutiveGreenMocks: inputs.consecutiveGreenMocks,
  };
}

function emptyPosterior(): PosteriorEstimate {
  return { mean: 0, lower: 0, upper: 0, nObservations: 0 };
}

/** Map a skill name to its display order (CO → CE → EE → EO). */
export const skillDisplayOrder: Record<Skill, number> = {
  CO: 0,
  CE: 1,
  EE: 2,
  EO: 3,
};
