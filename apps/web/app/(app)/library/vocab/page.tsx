import { Card } from "@/components/ui/Card";

const WORDS = [
  { id: "w1", lemma: "logement", gloss: "housing", nclc: 6 },
  { id: "w2", lemma: "abordable", gloss: "affordable", nclc: 7 },
  { id: "w3", lemma: "loyer", gloss: "rent", nclc: 6 },
  { id: "w4", lemma: "zonage", gloss: "zoning", nclc: 9 },
];

export default function VocabPage() {
  return (
    <Card>
      <ul className="divide-y divide-border">
        {WORDS.map((w) => (
          <li key={w.id} className="flex items-center justify-between py-2">
            <span className="font-semibold">{w.lemma}</span>
            <span className="text-sm text-muted">{w.gloss}</span>
            <span className="num text-xs text-muted">NCLC {w.nclc}+</span>
            <button aria-label={`Play ${w.lemma}`} className="min-h-tap min-w-tap">▶</button>
          </li>
        ))}
      </ul>
    </Card>
  );
}
