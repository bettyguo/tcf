import { describe, expect, it } from "vitest";

// Phase 1 smoke: vitest is wired and runs at least one assertion.
// Phase 8 introduces React Testing Library + Playwright suites.

describe("vitest smoke", () => {
  it("runs", () => {
    expect(1 + 1).toBe(2);
  });

  it("imports something Next-shaped without crashing", async () => {
    const mod = await import("../app/page");
    expect(typeof mod.default).toBe("function");
  });
});
