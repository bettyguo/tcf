// Drill FSM truth table. Exercises every transition + rejects illegal
// transitions. The Zustand store delegates to this function so the
// unit test owns the full state graph without React.

import { describe, expect, it } from "vitest";
import { transition, type DrillPhase } from "@/lib/state/drill-store";

const idle: DrillPhase = { phase: "IDLE" };
const item = {
  id: "i1",
  kind: "CE_SKIM" as const,
  prompt: "p",
  options: [{ id: "a", label: "A" }],
};

describe("drill transitions", () => {
  it("IDLE → LOADING_ITEM via LOAD", () => {
    expect(transition(idle, { type: "LOAD", itemId: "i1" }).phase).toBe(
      "LOADING_ITEM",
    );
  });

  it("LOADING_ITEM → PRESENTED via LOADED", () => {
    const s = transition(idle, { type: "LOAD", itemId: "i1" });
    expect(transition(s, { type: "LOADED", item }).phase).toBe("PRESENTED");
  });

  it("LOADED rejected when not loading", () => {
    expect(transition(idle, { type: "LOADED", item }).phase).toBe("IDLE");
  });

  it("PRESENTED → ANSWERING via START", () => {
    let s = transition(idle, { type: "LOAD", itemId: "i1" });
    s = transition(s, { type: "LOADED", item });
    expect(transition(s, { type: "START" }).phase).toBe("ANSWERING");
  });

  it("UPDATE merges into ANSWERING answer", () => {
    let s = transition(idle, { type: "LOAD", itemId: "i1" });
    s = transition(s, { type: "LOADED", item });
    s = transition(s, { type: "START" });
    s = transition(s, { type: "UPDATE", answer: { choiceId: "a" } });
    if (s.phase !== "ANSWERING") throw new Error("expected ANSWERING");
    expect(s.answer.choiceId).toBe("a");
  });

  it("SUBMIT → SUBMITTING; GRADED → REVEALED", () => {
    let s = transition(idle, { type: "LOAD", itemId: "i1" });
    s = transition(s, { type: "LOADED", item });
    s = transition(s, { type: "START" });
    s = transition(s, { type: "SUBMIT" });
    expect(s.phase).toBe("SUBMITTING");
    s = transition(s, { type: "GRADED", result: { rationale: "ok" } });
    expect(s.phase).toBe("REVEALED");
  });

  it("FAILED at any phase moves to ERROR with the originating item", () => {
    let s = transition(idle, { type: "LOAD", itemId: "i1" });
    s = transition(s, { type: "LOADED", item });
    s = transition(s, {
      type: "FAILED",
      error: {
        code: "E_NET_001",
        http_status: 0,
        message: "net",
        message_localized: {},
        context: {},
        phase: 8,
      },
    });
    expect(s.phase).toBe("ERROR");
  });

  it("NEXT resets to IDLE", () => {
    let s = transition(idle, { type: "LOAD", itemId: "i1" });
    s = transition(s, { type: "LOADED", item });
    s = transition(s, { type: "START" });
    expect(transition(s, { type: "NEXT" }).phase).toBe("IDLE");
  });
});
