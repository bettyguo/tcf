// UI preference store: persisted to localStorage, mirrored to IDB for
// early read on next session. Drives the accessibility settings page
// + the theme attribute on <html>.

"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { Locale } from "@/lib/i18n/config";
import { writePrefs } from "@/lib/persistence/idb";

export type ThemePref = "auto" | "light" | "dark" | "hc";
export type TextSize = "S" | "M" | "L" | "XL";
export type FontPref = "system" | "dyslexic";
export type MotionPref = "auto" | "always" | "never";

interface UiStore {
  locale: Locale;
  theme: ThemePref;
  textSize: TextSize;
  font: FontPref;
  motion: MotionPref;
  captionsDefault: boolean;
  bottomSheetOpen: boolean;
  setLocale: (l: Locale) => void;
  setTheme: (t: ThemePref) => void;
  setTextSize: (s: TextSize) => void;
  setFont: (f: FontPref) => void;
  setMotion: (m: MotionPref) => void;
  setCaptionsDefault: (v: boolean) => void;
  openSheet: () => void;
  closeSheet: () => void;
}

export const useUiStore = create<UiStore>()(
  persist(
    (set, get) => {
      const mirror = () => {
        const s = get();
        void writePrefs({
          locale: s.locale,
          theme: s.theme,
          textSize: s.textSize,
          font: s.font,
          motion: s.motion,
          captionsDefault: s.captionsDefault,
        });
      };
      return {
        locale: "en",
        theme: "auto",
        textSize: "M",
        font: "system",
        motion: "auto",
        captionsDefault: false,
        bottomSheetOpen: false,
        setLocale: (l) => {
          set({ locale: l });
          mirror();
        },
        setTheme: (t) => {
          set({ theme: t });
          mirror();
        },
        setTextSize: (s) => {
          set({ textSize: s });
          mirror();
        },
        setFont: (f) => {
          set({ font: f });
          mirror();
        },
        setMotion: (m) => {
          set({ motion: m });
          mirror();
        },
        setCaptionsDefault: (v) => {
          set({ captionsDefault: v });
          mirror();
        },
        openSheet: () => set({ bottomSheetOpen: true }),
        closeSheet: () => set({ bottomSheetOpen: false }),
      };
    },
    {
      name: "tcf-accel-ui",
      storage: createJSONStorage(() =>
        typeof window === "undefined"
          ? ({
              getItem: () => null,
              setItem: () => undefined,
              removeItem: () => undefined,
            } as Storage)
          : window.localStorage,
      ),
    },
  ),
);
