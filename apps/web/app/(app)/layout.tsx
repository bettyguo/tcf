// Authed shell: header + content + bottom nav (mobile) / sidebar
// (lg+). The Mock-Exam runner and onboarding screens are intentionally
// OUTSIDE this layout so they own the full viewport.

import type { ReactNode } from "react";
import { Header } from "@/components/nav/Header";
import { BottomNav } from "@/components/nav/BottomNav";
import { StubLocaleBanner } from "@/components/nav/StubLocaleBanner";

export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[16rem_1fr]">
      <aside className="hidden lg:block lg:border-r lg:border-border lg:p-4">
        <Header />
        <BottomNav />
      </aside>
      <div className="lg:contents">
        <div className="lg:hidden">
          <Header />
        </div>
        <main className="mx-auto w-full max-w-3xl px-4 pb-24 pt-4 lg:pb-8">
          <StubLocaleBanner />
          {children}
        </main>
        <div className="lg:hidden">
          <BottomNav />
        </div>
      </div>
    </div>
  );
}
