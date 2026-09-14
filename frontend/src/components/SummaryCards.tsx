import type { Summary } from "../api/types";

export default function SummaryCards({ summary, filtered }: { summary: Summary; filtered: boolean }) {
  const cards: Array<{ key: keyof Summary; label: string; className: string }> = [
    { key: "total", label: "Total", className: "c-total" },
    { key: "improved", label: "Improved", className: "c-improved" },
    { key: "regressed", label: "Regressed", className: "c-regressed" },
    { key: "unchanged", label: "Unchanged", className: "c-unchanged" },
    { key: "needsReview", label: "Needs review", className: "c-needs-review" },
    { key: "failed", label: "Failed", className: "c-failed" },
  ];
  return (
    <div className="summary-cards">
      {filtered && <p className="filtered-note">Showing filtered counts</p>}
      {cards.map(({ key, label, className }) => (
        <div key={key} className={`summary-card ${className}`}>
          <span className="summary-count">{summary[key] as number}</span>
          <span className="summary-label">{label}</span>
        </div>
      ))}
    </div>
  );
}
