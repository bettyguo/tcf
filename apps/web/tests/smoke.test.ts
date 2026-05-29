import { describe, expect, it } from "vitest";

describe("vitest smoke", () => {
  it("runs", () => {
    expect(1 + 1).toBe(2);
  });

  it("imports the root page module", async () => {
    const mod = await import("../app/page");
    expect(typeof mod.default).toBe("function");
  });

  it("imports lib/types", async () => {
    const mod = await import("@/lib/types");
    expect(mod.skills.length).toBe(4);
  });
});
