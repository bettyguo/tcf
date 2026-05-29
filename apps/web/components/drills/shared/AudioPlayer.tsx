// AudioPlayer — used by CO drills. The transcript is gated behind the
// REVEALED phase (else CO becomes a trivial reading exercise). Keyboard
// shortcut: Space toggles play/pause when focus is within the player.

"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";

interface Props {
  src: string;
  transcript?: string;
  showTranscript: boolean;
  singlePlay?: boolean; // ADR-029: CO single-play suppresses replay
}

export function AudioPlayer({
  src,
  transcript,
  showTranscript,
  singlePlay = false,
}: Props) {
  const t = useTranslations("drill");
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [played, setPlayed] = useState(false);

  useEffect(() => {
    const el = audioRef.current;
    if (!el) return;
    const onPlay = () => setPlaying(true);
    const onPause = () => setPlaying(false);
    const onEnded = () => {
      setPlaying(false);
      setPlayed(true);
    };
    el.addEventListener("play", onPlay);
    el.addEventListener("pause", onPause);
    el.addEventListener("ended", onEnded);
    return () => {
      el.removeEventListener("play", onPlay);
      el.removeEventListener("pause", onPause);
      el.removeEventListener("ended", onEnded);
    };
  }, []);

  const toggle = () => {
    const el = audioRef.current;
    if (!el) return;
    if (singlePlay && played) return;
    if (el.paused) void el.play();
    else el.pause();
  };

  return (
    <div
      className="flex flex-col gap-2"
      onKeyDown={(e) => {
        if (e.key === " " || e.key === "Spacebar") {
          e.preventDefault();
          toggle();
        }
      }}
    >
      <button
        type="button"
        onClick={toggle}
        aria-pressed={playing}
        disabled={singlePlay && played}
        className="min-h-tap rounded-md border border-border bg-card px-4 text-sm font-medium disabled:opacity-50"
      >
        {playing ? t("pause") : played && singlePlay ? "Played" : t("play")}
      </button>
      <audio ref={audioRef} src={src} preload="auto" className="sr-only">
        <track kind="captions" />
      </audio>
      {showTranscript && transcript && (
        <details open className="mt-2 text-sm">
          <summary className="cursor-pointer">{t("hideTranscript")}</summary>
          <p className="mt-1 whitespace-pre-wrap">{transcript}</p>
        </details>
      )}
    </div>
  );
}
