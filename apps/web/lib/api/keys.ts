// Typed query-key factory (phase8_design.md §5.1). Centralising the
// keys avoids the `["plan", "today"]` vs `["plan/today"]` drift that
// quietly breaks invalidations.

import type { Skill } from "@/lib/types";

export const qk = {
  me: () => ["me"] as const,
  plan: () => ["plan"] as const,
  todayBlocks: () => ["plan", "today"] as const,
  insights: () => ["insights"] as const,
  skill: (s: Skill) => ["insights", "skill", s] as const,
  errors: () => ["insights", "errors"] as const,
  readiness: () => ["insights", "readiness"] as const,
  mockHistory: () => ["mock-exam", "history"] as const,
  mockReport: (id: string) => ["mock-exam", "report", id] as const,
  libraryGrammar: () => ["library", "grammar"] as const,
  libraryVocab: () => ["library", "vocab"] as const,
  libraryWriting: () => ["library", "writing"] as const,
  librarySpeaking: () => ["library", "speaking"] as const,
  libraryCulture: () => ["library", "culture"] as const,
} as const;
