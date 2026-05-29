// The DrillPlayer FSM (phase8_design.md §4). Pure transitions in the
// store; side effects (audio, IDB, API) live in middleware so the
// transitions remain unit-testable.

"use client";

import { create } from "zustand";
import type { DrillKind, ErrorEnvelope } from "@/lib/types";

export interface DrillItem {
  id: string;
  kind: DrillKind;
  prompt: string;
  audioUrl?: string;
  transcript?: string;
  options?: { id: string; label: string }[];
  timeLimitSeconds?: number;
}

export interface DrillAnswer {
  choiceId?: string;
  text?: string;
  audioBlob?: Blob;
}

export interface GradeResult {
  correct?: boolean;
  rationale: string;
  score?: number;
}

export type DrillPhase =
  | { phase: "IDLE" }
  | { phase: "LOADING_ITEM"; itemId: string }
  | { phase: "PRESENTED"; item: DrillItem; startedAt: number }
  | {
      phase: "ANSWERING";
      item: DrillItem;
      answer: DrillAnswer;
      startedAt: number;
    }
  | { phase: "SUBMITTING"; item: DrillItem; answer: DrillAnswer }
  | {
      phase: "REVEALED";
      item: DrillItem;
      answer: DrillAnswer;
      result: GradeResult;
    }
  | { phase: "ERROR"; item?: DrillItem; error: ErrorEnvelope };

interface DrillStore {
  state: DrillPhase;
  load: (itemId: string) => void;
  loaded: (item: DrillItem) => void;
  startAnswering: () => void;
  updateAnswer: (a: DrillAnswer) => void;
  submit: () => void;
  graded: (result: GradeResult) => void;
  failed: (error: ErrorEnvelope) => void;
  next: () => void;
  reset: () => void;
}

export const useDrillStore = create<DrillStore>((set) => ({
  state: { phase: "IDLE" },
  load: (itemId) => set({ state: { phase: "LOADING_ITEM", itemId } }),
  loaded: (item) =>
    set({ state: { phase: "PRESENTED", item, startedAt: Date.now() } }),
  startAnswering: () =>
    set(({ state }) => {
      if (state.phase !== "PRESENTED") return { state };
      return {
        state: {
          phase: "ANSWERING",
          item: state.item,
          answer: {},
          startedAt: state.startedAt,
        },
      };
    }),
  updateAnswer: (a) =>
    set(({ state }) => {
      if (state.phase !== "ANSWERING") return { state };
      return {
        state: { ...state, answer: { ...state.answer, ...a } },
      };
    }),
  submit: () =>
    set(({ state }) => {
      if (state.phase !== "ANSWERING") return { state };
      return {
        state: {
          phase: "SUBMITTING",
          item: state.item,
          answer: state.answer,
        },
      };
    }),
  graded: (result) =>
    set(({ state }) => {
      if (state.phase !== "SUBMITTING") return { state };
      return {
        state: {
          phase: "REVEALED",
          item: state.item,
          answer: state.answer,
          result,
        },
      };
    }),
  failed: (error) =>
    set(({ state }) => ({
      state: {
        phase: "ERROR",
        item: "item" in state ? state.item : undefined,
        error,
      },
    })),
  next: () => set({ state: { phase: "IDLE" } }),
  reset: () => set({ state: { phase: "IDLE" } }),
}));

// Pure transition table — exported for unit tests so we exercise the
// truth table without spinning up React.
export type DrillEvent =
  | { type: "LOAD"; itemId: string }
  | { type: "LOADED"; item: DrillItem }
  | { type: "START" }
  | { type: "UPDATE"; answer: DrillAnswer }
  | { type: "SUBMIT" }
  | { type: "GRADED"; result: GradeResult }
  | { type: "FAILED"; error: ErrorEnvelope }
  | { type: "NEXT" };

export function transition(state: DrillPhase, event: DrillEvent): DrillPhase {
  switch (event.type) {
    case "LOAD":
      return { phase: "LOADING_ITEM", itemId: event.itemId };
    case "LOADED":
      if (state.phase !== "LOADING_ITEM") return state;
      return { phase: "PRESENTED", item: event.item, startedAt: Date.now() };
    case "START":
      if (state.phase !== "PRESENTED") return state;
      return {
        phase: "ANSWERING",
        item: state.item,
        answer: {},
        startedAt: state.startedAt,
      };
    case "UPDATE":
      if (state.phase !== "ANSWERING") return state;
      return { ...state, answer: { ...state.answer, ...event.answer } };
    case "SUBMIT":
      if (state.phase !== "ANSWERING") return state;
      return { phase: "SUBMITTING", item: state.item, answer: state.answer };
    case "GRADED":
      if (state.phase !== "SUBMITTING") return state;
      return {
        phase: "REVEALED",
        item: state.item,
        answer: state.answer,
        result: event.result,
      };
    case "FAILED":
      return {
        phase: "ERROR",
        item: "item" in state ? state.item : undefined,
        error: event.error,
      };
    case "NEXT":
      return { phase: "IDLE" };
    default: {
      const _exhaustive: never = event;
      return _exhaustive;
    }
  }
}
