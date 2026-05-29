"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/Card";

export default function ApiKeysPage() {
  const enabled = process.env.NEXT_PUBLIC_SELF_HOST === "1";
  if (!enabled) {
    return (
      <Card>
        <p className="text-sm text-muted">
          API key configuration is available on self-hosted deployments only.
        </p>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>API keys (self-host)</CardTitle>
      </CardHeader>
      <form className="space-y-3">
        <Field name="llm_url" label="LLM gateway URL" />
        <Field name="llm_key" label="LLM gateway key" type="password" />
        <Field name="asr_url" label="ASR backend URL" />
      </form>
    </Card>
  );
}

function Field({
  name,
  label,
  type = "text",
}: {
  name: string;
  label: string;
  type?: string;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-muted">{label}</span>
      <input
        name={name}
        type={type}
        className="min-h-tap rounded-md border border-border bg-card px-2"
      />
    </label>
  );
}
