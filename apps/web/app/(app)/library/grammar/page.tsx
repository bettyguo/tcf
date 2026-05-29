import { Card, CardHeader, CardTitle } from "@/components/ui/Card";

const LESSONS = [
  { id: "g1", nclc: 6, title: "Past tense agreement: passé composé with être" },
  { id: "g2", nclc: 7, title: "Connecteurs: puisque vs parce que" },
  { id: "g3", nclc: 8, title: "Subjunctive after expressions of doubt" },
  { id: "g4", nclc: 9, title: "Inversion in formal questions" },
  { id: "g5", nclc: 10, title: "Hedging and concession in argument" },
];

export default function GrammarPage() {
  return (
    <ul className="space-y-3">
      {LESSONS.map((l) => (
        <li key={l.id}>
          <Card>
            <CardHeader>
              <CardTitle>{l.title}</CardTitle>
              <span className="num text-xs text-muted">NCLC {l.nclc}+</span>
            </CardHeader>
            <p className="text-sm text-muted">
              Short lesson and two warm-ups. Drill linked below.
            </p>
            <button className="mt-3 min-h-tap rounded-md border border-border px-3 text-sm">
              Drill this
            </button>
          </Card>
        </li>
      ))}
    </ul>
  );
}
