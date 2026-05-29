"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

export default function MockStart() {
  const t = useTranslations("mockExam");
  const router = useRouter();
  const [mode, setMode] = useState<"canonical" | "training">("training");
  return (
    <main className="mx-auto max-w-xl px-4 py-8">
      <h1 className="text-2xl font-semibold">{t("start")}</h1>
      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Mode</CardTitle>
          <Badge tone={mode === "canonical" ? "accent" : "warning"}>
            {mode === "canonical" ? "🟦 CANONICAL" : "🟧 TRAINING"}
          </Badge>
        </CardHeader>
        <div role="radiogroup" className="space-y-3">
          <label className="flex items-start gap-3">
            <input
              type="radio"
              name="mode"
              value="training"
              checked={mode === "training"}
              onChange={() => setMode("training")}
            />
            <span>
              <span className="font-semibold">{t("training")}</span>
              <span className="block text-sm text-muted">{t("trainingNote")}</span>
            </span>
          </label>
          <label className="flex items-start gap-3">
            <input
              type="radio"
              name="mode"
              value="canonical"
              checked={mode === "canonical"}
              onChange={() => setMode("canonical")}
            />
            <span>
              <span className="font-semibold">{t("canonical")}</span>
              <span className="block text-sm text-muted">{t("canonicalNote")}</span>
            </span>
          </label>
        </div>
        <Button
          className="mt-4"
          onClick={() => router.push(`/mock-exam/run/new?mode=${mode}`)}
        >
          {t("start")}
        </Button>
      </Card>
    </main>
  );
}
