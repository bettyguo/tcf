// Shared domain types used by the frontend. These shadow a subset of the
// Phase 2 schemas in `packages/shared` so that the UI can compile without
// pulling Python contracts via codegen on every dev iteration. The
// generated openapi types in `@tcf-accel/client` remain the source of
// truth for network payloads.

export type Skill = "CO" | "CE" | "EE" | "EO";

export const skills: readonly Skill[] = ["CO", "CE", "EE", "EO"] as const;

/** Bounded NCLC (1..12) inclusive, per the Phase 4 model. */
export type Nclc = number;

export interface PosteriorEstimate {
  mean: Nclc;
  lower: Nclc; // 95% CI lower bound
  upper: Nclc; // 95% CI upper bound
  nObservations: number;
}

export interface SkillSnapshot {
  at: string; // ISO 8601
  posterior: PosteriorEstimate;
}

export interface SkillState {
  skill: Skill;
  posterior: PosteriorEstimate;
  history: SkillSnapshot[];
  target: Nclc;
}

export interface PlanBlock {
  id: string;
  index: number;
  skill: Skill;
  minutes: number;
  title: string;
  subtitle?: string;
  priority?: boolean;
  drillKind: DrillKind;
  status: "pending" | "in_progress" | "done";
}

export type DrillKind =
  | "CO_SINGLE_PLAY"
  | "CO_SHADOWING"
  | "CE_SKIM"
  | "CE_CLICK_DISTRACTOR"
  | "EE_TIMED_WRITE"
  | "EO_PICTURE"
  | "EO_COMPARE_CONTRAST"
  | "EO_OPINION";

export interface TodayPayload {
  userName: string;
  dayIndex: number;
  totalDays: number;
  minutesRemaining: number;
  blocks: PlanBlock[];
  rationale: string;
  resumeSessionId?: string;
}

export type ReadinessLight = "white" | "red" | "amber" | "green";

export type ReadinessState =
  | "INSUFFICIENT_DATA"
  | "NOT_READY"
  | "BORDERLINE"
  | "READY_ONE_MOCK"
  | "READY"
  | "REGRESSED";

export interface ReadinessSummary {
  state: ReadinessState;
  light: ReadinessLight;
  probability: number; // P(min ≥ target)
  bottleneck: Skill;
  bottleneckPosterior: PosteriorEstimate;
  target: Nclc;
  consecutiveGreenMocks: number; // canonical mocks at green in a row
}

export interface ErrorEnvelope {
  code: string;
  http_status: number;
  message: string;
  message_localized: Record<string, string>;
  context: Record<string, unknown>;
  phase: number | null;
}

export interface RubricDimension {
  key: string;
  label: string;
  score: number; // 0..5
  rationale: string;
  drillLink?: { kind: DrillKind; id: string };
  clamped?: boolean;
}

export interface MockReportSection {
  skill: Skill;
  nclc: Nclc;
  ci: [Nclc, Nclc];
  rubric?: { task: 1 | 2 | 3; dimensions: RubricDimension[] }[];
  spanAnnotated?: string;
  audioUrl?: string;
  transcript?: string;
}

export interface MockReportPayload {
  id: string;
  mode: "canonical" | "training";
  takenAt: string;
  overallNclc: Nclc;
  perSkill: MockReportSection[];
  inflationClamped: string[];
  nextSteps: { title: string; drill: DrillKind; id: string }[];
  kappa: number;
  kappaCalibratedAt: string;
}
