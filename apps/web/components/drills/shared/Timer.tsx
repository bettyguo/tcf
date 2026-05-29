// Timer — ARIA live region. Announces at 60/30/10/5/0 only, not every
// second (else it harasses screen-reader users).

"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

interface Props {
  startedAt: number;
  limitSeconds: number;
  onElapsed?: () => void;
}

const ANNOUNCE_AT = new Set([60, 30, 10, 5, 0]);

export function Timer({ startedAt, limitSeconds, onElapsed }: Props) {
  const t = useTranslations("drill");
  const [remaining, setRemaining] = useState(limitSeconds);
  const [liveText, setLiveText] = useState<string>("");

  useEffect(() => {
    const tick = () => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      const left = Math.max(0, limitSeconds - elapsed);
      setRemaining(left);
      if (ANNOUNCE_AT.has(left)) {
        setLiveText(t("timeLeft", { seconds: left }));
      }
      if (left === 0) onElapsed?.();
    };
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [startedAt, limitSeconds, onElapsed, t]);

  const danger = remaining <= 30;

  return (
    <>
      <span
        className={`num text-sm font-semibold ${danger ? "text-danger" : ""}`}
        aria-hidden="true"
      >
        {Math.floor(remaining / 60)}:
        {String(remaining % 60).padStart(2, "0")}
      </span>
      <span role="timer" aria-live="polite" className="sr-only">
        {liveText}
      </span>
    </>
  );
}
