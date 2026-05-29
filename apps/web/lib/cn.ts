// `cn` — the canonical shadcn class-merger. Avoids duplicate-utility
// pile-ups when composing variants.

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
