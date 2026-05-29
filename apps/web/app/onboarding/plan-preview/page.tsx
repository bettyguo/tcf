"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

export default function PlanPreviewPage() {
  const t = useTranslations("onboarding.planPreview");
  const router = useRouter();
  return (
    <section className="space-y-3">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>
      <Card>
        <CardHeader>
          <CardTitle>12-week plan</CardTitle>
        </CardHeader>
        <ul className="space-y-2 text-sm">
          <li>Weeks 1–2: EE foundations · CE skim · CO single-play.</li>
          <li>Weeks 3–6: EE Task 2 · EO picture · mock 1 (training).</li>
          <li>Weeks 7–9: EE Task 3 · EO opinion · mock 2 (training).</li>
          <li>Weeks 10–12: mock 1 + 2 (canonical) · light review.</li>
        </ul>
      </Card>
      <div className="flex gap-2">
        <Button
          onClick={() => {
            document.cookie = "tcf_auth=1; path=/; max-age=86400";
            document.cookie = "tcf_onboarded=1; path=/; max-age=86400";
            router.push("/today");
          }}
        >
          {t("accept")}
        </Button>
        <Button variant="ghost" onClick={() => router.push("/onboarding/goals")}>
          {t("adjust")}
        </Button>
      </div>
    </section>
  );
}
