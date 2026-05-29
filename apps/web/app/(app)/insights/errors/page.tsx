import { Card, CardHeader, CardTitle } from "@/components/ui/Card";

const PATTERNS = [
  { id: "p1", name: "Subjunctive after expressions of doubt", count: 24, drillUrl: "/today" },
  { id: "p2", name: "Gender of professional nouns", count: 18, drillUrl: "/today" },
  { id: "p3", name: "Connecteurs (puisque vs. parce que)", count: 12, drillUrl: "/today" },
];

export default function ErrorsPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recurrent error patterns</CardTitle>
      </CardHeader>
      <ul className="divide-y divide-border">
        {PATTERNS.map((p) => (
          <li key={p.id} className="flex items-center justify-between py-2 text-sm">
            <span>{p.name}</span>
            <span className="num text-muted">{p.count}×</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
