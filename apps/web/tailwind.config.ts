// Phase 8 design tokens (see phase8_design.md §8).
// Muted palette, no gradients, generous whitespace, mono for numerics.
// Light / dark / high-contrast via data-theme on <html>.

import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./stories/**/*.{ts,tsx}",
  ],
  darkMode: ["class", '[data-theme="dark"], [data-theme="hc"]'],
  theme: {
    extend: {
      colors: {
        bg: "var(--color-bg)",
        fg: "var(--color-fg)",
        muted: "var(--color-muted)",
        accent: "var(--color-accent)",
        danger: "var(--color-danger)",
        success: "var(--color-success)",
        warning: "var(--color-warning)",
        border: "var(--color-border)",
        card: "var(--color-card)",
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
        dyslexic: ["var(--font-dyslexic)"],
      },
      fontSize: {
        "2xs": ["11px", { lineHeight: "1.3" }],
        num: ["32px", { lineHeight: "1.0", fontFamily: "var(--font-mono)" }],
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "16px",
      },
      boxShadow: {
        "elev-1": "0 1px 2px 0 rgb(0 0 0 / 0.04)",
        "elev-2": "0 4px 12px -2px rgb(0 0 0 / 0.06)",
      },
      spacing: {
        tap: "44px",
      },
    },
  },
  plugins: [],
};

export default config;
