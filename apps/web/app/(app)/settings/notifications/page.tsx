"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";

// ADR-043: zero defaults. Copy is the lead, toggles are below.
export default function NotificationsPage() {
  const t = useTranslations("settings");
  const [daily, setDaily] = useState(false);
  const [mock, setMock] = useState(false);
  const [streak, setStreak] = useState(false);
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("notifications")}</CardTitle>
      </CardHeader>
      <p className="text-sm text-muted">{t("notificationsDefault")}</p>
      <div className="mt-4 space-y-3">
        <Toggle label="Daily reminder" checked={daily} onChange={setDaily} />
        <Toggle label="Mock-exam reminder" checked={mock} onChange={setMock} />
        <Toggle
          label="Streak-protection ping"
          description="Strongly recommend leaving off. Enable only if you have found you forget to open the app for multiple days at a time."
          checked={streak}
          onChange={setStreak}
        />
      </div>
    </Card>
  );
}

function Toggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-start justify-between gap-3 border-t border-border pt-3">
      <span>
        <span className="block text-sm font-medium">{label}</span>
        {description && (
          <span className="block text-sm text-muted">{description}</span>
        )}
      </span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 h-5 w-5"
      />
    </label>
  );
}
