// Thin IndexedDB wrapper used by drafts, mock-queue, audio cache, and
// the early-read accessibility prefs mirror. See phase8_design.md §5.5.
//
// Server-side renders no-op (typeof indexedDB === "undefined"); callers
// must tolerate undefined results during SSR.

import { get as idbGet, set as idbSet, del as idbDel, keys as idbKeys } from "idb-keyval";

const NS = "tcf-accel";

function key(store: string, id: string): string {
  return `${NS}:${store}:${id}`;
}

export async function readDraft<T>(promptId: string): Promise<T | undefined> {
  if (typeof indexedDB === "undefined") return undefined;
  return (await idbGet(key("drafts", promptId))) as T | undefined;
}

export async function writeDraft<T>(promptId: string, value: T): Promise<void> {
  if (typeof indexedDB === "undefined") return;
  await idbSet(key("drafts", promptId), value);
}

export async function clearDraft(promptId: string): Promise<void> {
  if (typeof indexedDB === "undefined") return;
  await idbDel(key("drafts", promptId));
}

export interface QueuedMockAnswer {
  mockId: string;
  itemId: string;
  answer: unknown;
  queuedAt: number;
  submittedAt?: number;
}

export async function enqueueMockAnswer(a: QueuedMockAnswer): Promise<void> {
  if (typeof indexedDB === "undefined") return;
  await idbSet(key("mockQueue", `${a.mockId}:${a.itemId}`), a);
}

export async function pendingMockAnswers(): Promise<QueuedMockAnswer[]> {
  if (typeof indexedDB === "undefined") return [];
  const allKeys = (await idbKeys()) as string[];
  const out: QueuedMockAnswer[] = [];
  for (const k of allKeys) {
    if (!k.startsWith(`${NS}:mockQueue:`)) continue;
    const v = (await idbGet(k)) as QueuedMockAnswer | undefined;
    if (v && !v.submittedAt) out.push(v);
  }
  return out;
}

export async function markMockAnswerSubmitted(mockId: string, itemId: string): Promise<void> {
  if (typeof indexedDB === "undefined") return;
  await idbDel(key("mockQueue", `${mockId}:${itemId}`));
}

export interface PrefsSnapshot {
  locale: string;
  theme: "auto" | "light" | "dark" | "hc";
  textSize: "S" | "M" | "L" | "XL";
  font: "system" | "dyslexic";
  motion: "auto" | "always" | "never";
  captionsDefault: boolean;
}

export async function readPrefs(): Promise<PrefsSnapshot | undefined> {
  if (typeof indexedDB === "undefined") return undefined;
  return (await idbGet(key("prefs", "current"))) as PrefsSnapshot | undefined;
}

export async function writePrefs(p: PrefsSnapshot): Promise<void> {
  if (typeof indexedDB === "undefined") return;
  await idbSet(key("prefs", "current"), p);
}
