"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/Button";

export default function GoalsPage() {
  const t = useTranslations("onboarding.goals");
  const router = useRouter();
  const [target, setTarget] = useState(9);
  const [date, setDate] = useState("");
  const [budget, setBudget] = useState(30);
  const [l1, setL1] = useState("");

  return (
    <section>
      <h1 className="text-2xl font-semibold">{t("title")}</h1>
      <form
        className="mt-4 space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          router.push("/onboarding/diagnostic");
        }}
      >
        <label className="block">
          <span className="text-sm text-muted">{t("targetNclc")}</span>
          <input
            type="number"
            min={1}
            max={12}
            value={target}
            onChange={(e) => setTarget(Number(e.target.value))}
            className="block w-full min-h-tap rounded-md border border-border bg-card px-3"
            required
          />
        </label>
        <label className="block">
          <span className="text-sm text-muted">{t("examDate")}</span>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="block w-full min-h-tap rounded-md border border-border bg-card px-3"
          />
        </label>
        <label className="block">
          <span className="text-sm text-muted">{t("dailyBudget")}</span>
          <input
            type="range"
            min={15}
            max={120}
            step={5}
            value={budget}
            onChange={(e) => setBudget(Number(e.target.value))}
            className="block w-full"
          />
          <span className="num text-sm">{budget} min</span>
        </label>
        <label className="block">
          <span className="text-sm text-muted">{t("l1")}</span>
          <input
            value={l1}
            onChange={(e) => setL1(e.target.value)}
            className="block w-full min-h-tap rounded-md border border-border bg-card px-3"
          />
        </label>
        <Button type="submit">{t("next")}</Button>
      </form>
    </section>
  );
}
