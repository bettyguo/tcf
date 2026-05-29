// DrillPlayer — the universal state machine UI. Reads from the Zustand
// drill store; delegates per-type rendering to the small per-drill
// components under components/drills/. Keyboard shortcuts: Space play/
// pause (forwarded to AudioPlayer), Enter submit, Esc end-with-confirm.

"use client";

import { useEffect, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { useDrillStore, type DrillItem } from "@/lib/state/drill-store";
import { writeDraft } from "@/lib/persistence/idb";
import { Button } from "@/components/ui/Button";
import { AudioPlayer } from "@/components/drills/shared/AudioPlayer";
import { Timer } from "@/components/drills/shared/Timer";

interface Props {
  item?: DrillItem;
  onSubmit: (answer: unknown) => Promise<unknown>;
  onNext?: () => void;
  onEnd?: () => void;
  showTranscript?: boolean;
  showRationale?: boolean; // false in canonical mock mode
}

export function DrillPlayer({
  item,
  onSubmit,
  onNext,
  onEnd,
  showTranscript = false,
  showRationale = true,
}: Props): ReactNode {
  const t = useTranslations("drill");
  const { state, loaded, startAnswering, updateAnswer, submit, graded, failed, next } =
    useDrillStore();

  // Auto-load when an item is provided.
  useEffect(() => {
    if (!item) return;
    if (state.phase === "IDLE" || state.phase === "LOADING_ITEM") {
      loaded(item);
    }
  }, [item, state.phase, loaded]);

  useEffect(() => {
    if (state.phase !== "PRESENTED") return;
    startAnswering();
  }, [state.phase, startAnswering]);

  // Autosave EE drafts on every typed update.
  useEffect(() => {
    if (state.phase !== "ANSWERING") return;
    if (typeof state.answer.text !== "string") return;
    void writeDraft(state.item.id, state.answer.text);
  }, [state]);

  if (!item || state.phase === "IDLE" || state.phase === "LOADING_ITEM") {
    return <p className="text-sm text-muted">{t("loading")}</p>;
  }
  if (state.phase === "ERROR") {
    return (
      <p role="alert" className="text-sm text-danger">
        {state.error.message}
      </p>
    );
  }

  const active = state.item;
  const isCO = active.kind.startsWith("CO_");
  const isEE = active.kind === "EE_TIMED_WRITE";
  const isMcq =
    active.kind === "CE_SKIM" || active.kind === "CE_CLICK_DISTRACTOR";

  const doSubmit = async () => {
    submit();
    try {
      const result = (await onSubmit(
        state.phase === "ANSWERING" || state.phase === "SUBMITTING"
          ? state.answer
          : {},
      )) as { rationale: string; correct?: boolean; score?: number };
      graded(result);
    } catch (e) {
      failed({
        code: "E_NET_001",
        http_status: 0,
        message: t("loading"),
        message_localized: {},
        context: {},
        phase: 8,
      });
      throw e;
    }
  };

  return (
    <section
      className="space-y-4"
      onKeyDown={(e) => {
        if (e.key === "Enter" && state.phase === "ANSWERING") {
          e.preventDefault();
          void doSubmit();
        }
        if (e.key === "Escape" && onEnd) {
          e.preventDefault();
          onEnd();
        }
      }}
    >
      <header className="flex items-center justify-between gap-2">
        <p className="text-sm text-muted">{active.kind.replace("_", " ")}</p>
        {active.timeLimitSeconds && state.phase === "ANSWERING" && (
          <Timer
            startedAt={state.startedAt}
            limitSeconds={active.timeLimitSeconds}
            onElapsed={() => void doSubmit()}
          />
        )}
      </header>

      <p className="text-base">{active.prompt}</p>

      {isCO && active.audioUrl && (
        <AudioPlayer
          src={active.audioUrl}
          transcript={active.transcript}
          showTranscript={showTranscript && state.phase === "REVEALED"}
          singlePlay={active.kind === "CO_SINGLE_PLAY"}
        />
      )}

      {isMcq && active.options && state.phase === "ANSWERING" && (
        <ul className="space-y-2" role="radiogroup" aria-label={t("answerHere")}>
          {active.options.map((o) => (
            <li key={o.id}>
              <button
                role="radio"
                aria-checked={
                  state.phase === "ANSWERING"
                    ? state.answer.choiceId === o.id
                    : false
                }
                onClick={() => updateAnswer({ choiceId: o.id })}
                className="min-h-tap w-full rounded-md border border-border bg-card px-4 text-left text-sm font-medium hover:bg-bg"
              >
                {o.label}
              </button>
            </li>
          ))}
        </ul>
      )}

      {isEE && state.phase === "ANSWERING" && (
        <label className="block">
          <span className="sr-only">{t("answerHere")}</span>
          <textarea
            className="w-full min-h-[14rem] rounded-md border border-border bg-card p-3 font-sans text-sm"
            value={state.answer.text ?? ""}
            onChange={(e) => updateAnswer({ text: e.target.value })}
            placeholder={t("answerHere")}
            spellCheck
            lang="fr"
          />
          <p className="num mt-1 text-xs text-muted" aria-live="polite">
            {t("saveDraft")}
          </p>
        </label>
      )}

      {state.phase === "ANSWERING" && (
        <Button onClick={() => void doSubmit()}>{t("submit")}</Button>
      )}

      {state.phase === "SUBMITTING" && (
        <p className="text-sm text-muted">{t("submitted")}</p>
      )}

      {state.phase === "REVEALED" && (
        <div className="space-y-3">
          {showRationale && (
            <details open className="rounded-md border border-border bg-card p-3 text-sm">
              <summary className="cursor-pointer font-medium">
                {t("hideRationale")}
              </summary>
              <p className="mt-2">{state.result.rationale}</p>
            </details>
          )}
          {onNext && (
            <Button variant="secondary" onClick={() => { next(); onNext(); }}>
              {t("next")}
            </Button>
          )}
          {onEnd && (
            <Button variant="ghost" onClick={onEnd}>
              {t("end")}
            </Button>
          )}
        </div>
      )}
    </section>
  );
}
