const CLASS_MAP: Record<string, string> = {
  "Improved": "c-improved",
  "Regressed": "c-regressed",
  "Unchanged": "c-unchanged",
  "Needs review": "c-needs-review",
  "Failed": "c-failed",
};

export default function ClassificationBadge({ classification }: { classification: string }) {
  return <span className={`badge ${CLASS_MAP[classification] ?? "c-unchanged"}`}>{classification}</span>;
}
