// Mock-Exam runner suppresses the app shell (no bottom nav, no header).
// Phase 8 design §10.1 / phase8_think.md §3.1.

import type { ReactNode } from "react";

export default function MockLayout({ children }: { children: ReactNode }) {
  return <div className="min-h-screen bg-bg">{children}</div>;
}
