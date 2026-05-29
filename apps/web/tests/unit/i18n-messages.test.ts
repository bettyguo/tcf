// Every locale's catalog must share key topology with en.json (the
// primary), so missing-key fallback is the only fallback path. Stub
// locales (es/ar/zh) are allowed to be sparse — they fall back to en
// at runtime.

import { describe, expect, it } from "vitest";
import en from "@/messages/en.json";
import fr from "@/messages/fr.json";

function leafKeys(obj: unknown, prefix = ""): string[] {
  if (obj && typeof obj === "object" && !Array.isArray(obj)) {
    return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) =>
      leafKeys(v, prefix ? `${prefix}.${k}` : k),
    );
  }
  return [prefix];
}

describe("i18n catalogs", () => {
  it("French has every key the English catalog has", () => {
    const enKeys = new Set(leafKeys(en));
    const frKeys = new Set(leafKeys(fr));
    const missing = [...enKeys].filter((k) => !frKeys.has(k));
    expect(missing).toEqual([]);
  });

  it("notifications copy has no banned urgency wording (ADR-043)", () => {
    const banned = /lost!|behind!|don't.*miss|hurry/i;
    const text = JSON.stringify({ en, fr });
    expect(banned.test(text)).toBe(false);
  });
});
