// Every state of the most-consequential widget gets a story. Covers
// ADR-045 corner: even with one canonical green mock the light is amber.

import type { Meta, StoryObj } from "@storybook/react";
import { ReadinessWidget } from "@/components/domain/ReadinessWidget";
import type {
  PosteriorEstimate,
  ReadinessState,
  ReadinessSummary,
} from "@/lib/types";

const meta: Meta<typeof ReadinessWidget> = {
  title: "Domain/ReadinessWidget",
  component: ReadinessWidget,
};
export default meta;

type Story = StoryObj<typeof ReadinessWidget>;

const posterior = (mean: number, lo: number, hi: number): PosteriorEstimate => ({
  mean,
  lower: lo,
  upper: hi,
  nObservations: 60,
});

function summary(state: ReadinessState, opts: Partial<ReadinessSummary> = {}): ReadinessSummary {
  return {
    state,
    light:
      state === "READY"
        ? "green"
        : state === "INSUFFICIENT_DATA"
          ? "white"
          : state === "READY_ONE_MOCK" || state === "BORDERLINE"
            ? "amber"
            : "red",
    probability: 0.5,
    bottleneck: "EE",
    bottleneckPosterior: posterior(8, 7, 9),
    target: 9,
    consecutiveGreenMocks: 0,
    ...opts,
  };
}

export const Insufficient: Story = {
  args: { summary: summary("INSUFFICIENT_DATA", { probability: 0 }) },
};
export const NotReady: Story = {
  args: { summary: summary("NOT_READY", { probability: 0.15, bottleneckPosterior: posterior(6, 5, 7) }) },
};
export const Borderline: Story = {
  args: { summary: summary("BORDERLINE", { probability: 0.6 }) },
};
export const ReadyOneMock: Story = {
  // ADR-045: 🟢 floored to 🟡 until ≥ 2 consecutive canonical greens.
  args: { summary: summary("READY_ONE_MOCK", { probability: 0.85, consecutiveGreenMocks: 1 }) },
};
export const Ready: Story = {
  args: {
    summary: summary("READY", {
      probability: 0.92,
      consecutiveGreenMocks: 2,
      bottleneckPosterior: posterior(9, 8, 10),
    }),
  },
};
export const Regressed: Story = {
  args: { summary: summary("REGRESSED", { probability: 0.4 }) },
};
