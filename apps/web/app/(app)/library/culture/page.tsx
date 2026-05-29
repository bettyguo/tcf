import { Card, CardHeader, CardTitle } from "@/components/ui/Card";

const TOPICS = [
  { id: "c1", title: "How CRA differs from the IRS" },
  { id: "c2", title: "Provincial vs. federal jurisdiction" },
  { id: "c3", title: "Idioms common in TCF passages" },
];

export default function CulturePage() {
  return (
    <ul className="space-y-3">
      {TOPICS.map((c) => (
        <li key={c.id}>
          <Card>
            <CardHeader>
              <CardTitle>{c.title}</CardTitle>
            </CardHeader>
            <p className="text-sm text-muted">Background reading at B1+ level.</p>
          </Card>
        </li>
      ))}
    </ul>
  );
}
