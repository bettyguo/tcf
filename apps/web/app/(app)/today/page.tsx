// Today screen — the default after login. RSC for the greeting + plan
// summary, CSC for the start buttons (TodayBlocks below).

import { getTranslations } from "next-intl/server";
import { TodayBlocks } from "./TodayBlocks";
import type { TodayPayload } from "@/lib/types";

async function getToday(): Promise<TodayPayload> {
  // In production this calls /v1/plan/today over fetch with the auth
  // cookie forwarded. For the Phase 8 scaffold we ship a deterministic
  // fixture so the page renders standalone in dev / Storybook / E2E.
  return {
    userName: "Aïcha",
    dayIndex: 23,
    totalDays: 84,
    minutesRemaining: 102,
    blocks: [
      {
        id: "b1",
        index: 1,
        skill: "EE",
        minutes: 30,
        title: "Task 2 timed write — Canadian housing",
        priority: true,
        drillKind: "EE_TIMED_WRITE",
        status: "pending",
      },
      {
        id: "b2",
        index: 2,
        skill: "EO",
        minutes: 20,
        title: "Picture description × 5",
        drillKind: "EO_PICTURE",
        status: "pending",
      },
      {
        id: "b3",
        index: 3,
        skill: "CE",
        minutes: 25,
        title: "Mixed-difficulty drills",
        drillKind: "CE_SKIM",
        status: "pending",
      },
      {
        id: "b4",
        index: 4,
        skill: "CO",
        minutes: 10,
        title: "Shadowing",
        drillKind: "CO_SHADOWING",
        status: "pending",
      },
    ],
    rationale:
      "EE is your bottleneck (NCLC 6, target 9). EO close behind. CO and CE are on track.",
  };
}

export default async function TodayPage() {
  const t = await getTranslations("today");
  const today = await getToday();
  const remaining =
    today.minutesRemaining >= 60
      ? `${Math.floor(today.minutesRemaining / 60)}h ${today.minutesRemaining % 60}m`
      : `${today.minutesRemaining}m`;
  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">
          {t("greeting", { name: today.userName })}
        </h1>
        <p className="num text-sm text-muted">
          {t("dayCounter", {
            day: today.dayIndex,
            total: today.totalDays,
            remaining,
          })}
        </p>
      </header>

      <TodayBlocks today={today} />

      <details className="text-sm">
        <summary className="cursor-pointer font-medium">
          ▾ {t("whyThisPlan")}
        </summary>
        <p className="mt-2 text-muted">{today.rationale}</p>
      </details>
    </div>
  );
}
