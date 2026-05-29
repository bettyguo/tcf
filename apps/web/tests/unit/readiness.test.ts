// Truth table for the readiness state machine. The widget never renders
// these states without going through this function (phase8_design.md
// §3.2 / ADR-045).

import { describe, expect, it } from "vitest";
import { deriveReadiness } from "@/lib/readiness";
import type { SkillState } from "@/lib/types";

const skillsAt = (mean: number): SkillState[] =>
  (["CO", "CE", "EE", "EO"] as const).map((s) => ({
    skill: s,
    target: 9,
    posterior: { mean, lower: mean - 1, upper: mean + 1, nObservations: 30 },
    history: [],
  }));

describe("deriveReadiness", () => {
  it("returns INSUFFICIENT_DATA before any canonical mock", () => {
    const s = deriveReadiness({
      skills: skillsAt(9),
      target: 9,
      canonicalMocksCompleted: 0,
      consecutiveGreenMocks: 0,
      probabilityMinAtTarget: 0.5,
    });
    expect(s.state).toBe("INSUFFICIENT_DATA");
    expect(s.light).toBe("white");
  });

  it("returns NOT_READY when bottleneck is well below target and p is low", () => {
    const s = deriveReadiness({
      skills: skillsAt(6),
      target: 9,
      canonicalMocksCompleted: 2,
      consecutiveGreenMocks: 0,
      probabilityMinAtTarget: 0.05,
    });
    expect(s.state).toBe("NOT_READY");
    expect(s.light).toBe("red");
  });

  it("returns BORDERLINE within 1 of target", () => {
    const s = deriveReadiness({
      skills: skillsAt(8),
      target: 9,
      canonicalMocksCompleted: 1,
      consecutiveGreenMocks: 0,
      probabilityMinAtTarget: 0.6,
    });
    expect(s.state).toBe("BORDERLINE");
    expect(s.light).toBe("amber");
  });

  it("ADR-045: 1 green canonical mock floors light to amber", () => {
    const s = deriveReadiness({
      skills: skillsAt(9),
      target: 9,
      canonicalMocksCompleted: 1,
      consecutiveGreenMocks: 1,
      probabilityMinAtTarget: 0.9,
    });
    expect(s.state).toBe("READY_ONE_MOCK");
    expect(s.light).toBe("amber");
  });

  it("returns READY only with ≥ 2 consecutive green mocks AND p ≥ 0.85", () => {
    const s = deriveReadiness({
      skills: skillsAt(9),
      target: 9,
      canonicalMocksCompleted: 2,
      consecutiveGreenMocks: 2,
      probabilityMinAtTarget: 0.9,
    });
    expect(s.state).toBe("READY");
    expect(s.light).toBe("green");
  });

  it("does NOT return READY when 2 mocks present but p < 0.85", () => {
    const s = deriveReadiness({
      skills: skillsAt(9),
      target: 9,
      canonicalMocksCompleted: 2,
      consecutiveGreenMocks: 2,
      probabilityMinAtTarget: 0.7,
    });
    // 2 green mocks but probability gate not cleared → still borderline.
    expect(s.state).toBe("BORDERLINE");
  });

  it("returns REGRESSED when flagged regardless of mean", () => {
    const s = deriveReadiness({
      skills: skillsAt(9),
      target: 9,
      canonicalMocksCompleted: 2,
      consecutiveGreenMocks: 0,
      probabilityMinAtTarget: 0.6,
      regressed: true,
    });
    expect(s.state).toBe("REGRESSED");
    expect(s.light).toBe("red");
  });

  it("picks the lowest-mean skill as the bottleneck", () => {
    const skills: SkillState[] = [
      { skill: "CO", target: 9, posterior: { mean: 9, lower: 8, upper: 10, nObservations: 30 }, history: [] },
      { skill: "CE", target: 9, posterior: { mean: 9, lower: 8, upper: 10, nObservations: 30 }, history: [] },
      { skill: "EE", target: 9, posterior: { mean: 7, lower: 6, upper: 8, nObservations: 30 }, history: [] },
      { skill: "EO", target: 9, posterior: { mean: 8.4, lower: 8, upper: 9, nObservations: 30 }, history: [] },
    ];
    const s = deriveReadiness({
      skills,
      target: 9,
      canonicalMocksCompleted: 1,
      consecutiveGreenMocks: 0,
      probabilityMinAtTarget: 0.4,
    });
    expect(s.bottleneck).toBe("EE");
    expect(s.bottleneckPosterior.mean).toBe(7);
  });
});
