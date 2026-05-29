"use client";

import { useTranslations } from "next-intl";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { useUiStore } from "@/lib/state/ui-store";
import { locales, localeLabels, type Locale } from "@/lib/i18n/config";

export default function AccessibilityPage() {
  const t = useTranslations("settings");
  const ui = useUiStore();
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("accessibility")}</CardTitle>
      </CardHeader>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label={t("fontSize")}>
          <select
            value={ui.textSize}
            onChange={(e) => ui.setTextSize(e.target.value as "S" | "M" | "L" | "XL")}
            className="min-h-tap rounded-md border border-border bg-card px-2"
          >
            {(["S", "M", "L", "XL"] as const).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t("contrast")}>
          <select
            value={ui.theme}
            onChange={(e) => ui.setTheme(e.target.value as typeof ui.theme)}
            className="min-h-tap rounded-md border border-border bg-card px-2"
          >
            <option value="auto">Auto</option>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="hc">High contrast</option>
          </select>
        </Field>
        <Field label={t("font")}>
          <select
            value={ui.font}
            onChange={(e) => ui.setFont(e.target.value as typeof ui.font)}
            className="min-h-tap rounded-md border border-border bg-card px-2"
          >
            <option value="system">System</option>
            <option value="dyslexic">OpenDyslexic</option>
          </select>
        </Field>
        <Field label={t("motion")}>
          <select
            value={ui.motion}
            onChange={(e) => ui.setMotion(e.target.value as typeof ui.motion)}
            className="min-h-tap rounded-md border border-border bg-card px-2"
          >
            <option value="auto">Auto (system)</option>
            <option value="always">Always</option>
            <option value="never">Never</option>
          </select>
        </Field>
        <Field label={t("captions")}>
          <input
            type="checkbox"
            checked={ui.captionsDefault}
            onChange={(e) => ui.setCaptionsDefault(e.target.checked)}
          />
        </Field>
        <Field label={t("language")}>
          <select
            value={ui.locale}
            onChange={(e) => ui.setLocale(e.target.value as Locale)}
            className="min-h-tap rounded-md border border-border bg-card px-2"
          >
            {locales.map((l) => (
              <option key={l} value={l}>
                {localeLabels[l]}
              </option>
            ))}
          </select>
        </Field>
      </div>
    </Card>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-muted">{label}</span>
      {children}
    </label>
  );
}
