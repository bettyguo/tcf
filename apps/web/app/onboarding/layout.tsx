// Onboarding sits outside the (app) shell — minimal chrome.

import type { ReactNode } from "react";

export default function OnboardingLayout({ children }: { children: ReactNode }) {
  return (
    <main className="mx-auto max-w-md px-4 py-8">
      <div className="mb-6 text-sm text-muted">tcf-accel</div>
      {children}
    </main>
  );
}
