import { describe, expect, it } from "vitest";
import {
  formatCi,
  formatMinutes,
  formatNclcMean,
  formatNclcWithCi,
  formatProbability,
} from "@/lib/format";

describe("formatters", () => {
  it("renders integers without trailing zeros", () => {
    expect(formatNclcMean(8)).toBe("8");
    expect(formatNclcMean(8.0)).toBe("8");
  });
  it("renders fractional means to 1 dp", () => {
    expect(formatNclcMean(8.34)).toBe("8.3");
  });
  it("formats CI with en-dash by default", () => {
    expect(
      formatCi({ mean: 8, lower: 7, upper: 9, nObservations: 1 }),
    ).toBe("7–9");
  });
  it("formats NCLC + CI as the ADR-025 string", () => {
    expect(
      formatNclcWithCi({ mean: 8, lower: 7, upper: 9, nObservations: 1 }),
    ).toBe("NCLC 8 (CI 7–9)");
  });
  it("formats probability to 2 decimal places", () => {
    expect(formatProbability(0.6234)).toBe("0.62");
  });
  it("formats minutes < 60 plainly", () => {
    expect(formatMinutes(30)).toBe("30 min");
  });
  it("formats minutes >= 60 as h+m", () => {
    expect(formatMinutes(102)).toBe("1h 42m");
    expect(formatMinutes(120)).toBe("2h");
  });
});
