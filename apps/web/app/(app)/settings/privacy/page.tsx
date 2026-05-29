"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

export default function PrivacyPage() {
  const t = useTranslations("settings");
  const [mode, setMode] = useState<"local" | "cloud">("local");
  const [confirmDelete, setConfirmDelete] = useState(false);
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("privacy")}</CardTitle>
      </CardHeader>
      <p className="text-sm text-muted">{t("privacyExplainer")}</p>
      <div role="radiogroup" className="mt-3 space-y-2">
        <label className="flex items-center gap-2">
          <input
            type="radio"
            name="mode"
            checked={mode === "local"}
            onChange={() => setMode("local")}
          />
          This device only (recommended)
        </label>
        <label className="flex items-center gap-2">
          <input
            type="radio"
            name="mode"
            checked={mode === "cloud"}
            onChange={() => setMode("cloud")}
          />
          Cloud sync
        </label>
      </div>
      {mode === "cloud" && (
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <p className="text-sm font-medium">{t("syncedItems")}</p>
            <ul className="list-disc pl-5 text-sm text-muted">
              <li>Plan and progress</li>
              <li>Mock-exam scores</li>
            </ul>
          </div>
          <div>
            <p className="text-sm font-medium">{t("notSyncedItems")}</p>
            <ul className="list-disc pl-5 text-sm text-muted">
              <li>Raw EE drafts</li>
              <li>Audio recordings</li>
            </ul>
          </div>
        </div>
      )}
      <div className="mt-6 flex flex-wrap gap-3">
        <Button variant="secondary">{t("exportMyData")}</Button>
        {!confirmDelete ? (
          <Button variant="danger" onClick={() => setConfirmDelete(true)}>
            {t("deleteAccount")}
          </Button>
        ) : (
          <span className="flex items-center gap-2">
            <Button variant="danger">Yes, delete everything</Button>
            <Button variant="ghost" onClick={() => setConfirmDelete(false)}>
              Cancel
            </Button>
          </span>
        )}
      </div>
    </Card>
  );
}
