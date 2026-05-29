import { Card, CardHeader, CardTitle } from "@/components/ui/Card";

const ESSAYS = [
  { id: "e1", nclc: 7, title: "Renting in a small Canadian city — pros and cons" },
  { id: "e2", nclc: 9, title: "On the affordability of urban housing" },
  { id: "e3", nclc: 11, title: "Zoning reform: a moral argument" },
];

export default function WritingPage() {
  return (
    <ul className="space-y-3">
      {ESSAYS.map((e) => (
        <li key={e.id}>
          <Card>
            <CardHeader>
              <CardTitle>{e.title}</CardTitle>
              <span className="num text-xs text-muted">NCLC {e.nclc}</span>
            </CardHeader>
            <p className="text-sm text-muted">Annotated for rubric components.</p>
          </Card>
        </li>
      ))}
    </ul>
  );
}
