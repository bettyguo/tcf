import { Card, CardHeader, CardTitle } from "@/components/ui/Card";

const RECS = [
  { id: "s1", nclc: 7, title: "Picture description — public transit" },
  { id: "s2", nclc: 9, title: "Compare/contrast — rural vs. urban" },
];

export default function SpeakingPage() {
  return (
    <ul className="space-y-3">
      {RECS.map((r) => (
        <li key={r.id}>
          <Card>
            <CardHeader>
              <CardTitle>{r.title}</CardTitle>
              <span className="num text-xs text-muted">NCLC {r.nclc}</span>
            </CardHeader>
            <p className="text-sm text-muted">Audio + rubric-aligned scoring overlay.</p>
          </Card>
        </li>
      ))}
    </ul>
  );
}
