// Phase 1: hello-world page only. Phase 8 elaborates the full screen tree
// (Today, Insights, Library, Mock Exam, Onboarding, Settings).

export default function Home() {
  return (
    <main
      style={{
        fontFamily:
          "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
        padding: "4rem 2rem",
        maxWidth: 720,
        margin: "0 auto",
        lineHeight: 1.6,
      }}
    >
      <h1 style={{ margin: 0 }}>tcf-accel</h1>
      <p style={{ color: "#555" }}>
        Phase 1 hello page. The real application begins in Phase 8.
      </p>
      <p>
        See the repository root for the planning docs (
        <code>00_MASTER_PROMPT.md</code> through <code>09_*.md</code>) and the
        per-phase artifacts.
      </p>
    </main>
  );
}
