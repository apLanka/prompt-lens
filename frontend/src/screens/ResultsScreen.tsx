import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { getRun, ApiError } from "../api/client";
import type { RunCaseResult, RunWithResults } from "../api/types";
import ErrorBanner from "../components/ErrorBanner";
import SummaryCards from "../components/SummaryCards";
import ClassificationBadge from "../components/ClassificationBadge";

const CLASSIFICATIONS = ["Improved", "Regressed", "Unchanged", "Needs review", "Failed"];

export default function ResultsScreen() {
  const { runId } = useParams<{ runId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [run, setRun] = useState<RunWithResults | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const seqRef = useRef(0);

  const classification = searchParams.get("classification") ?? undefined;
  const tagsParam = searchParams.get("tags");
  const tags = tagsParam ? tagsParam.split(",").map((t) => t.trim()).filter(Boolean) : undefined;

  const load = useCallback(async () => {
    if (!runId) return;
    const seq = ++seqRef.current;
    setLoading(true);
    setError("");
    try {
      const data = await getRun(runId, { classification, tags: tags?.length ? tags : undefined });
      if (seq === seqRef.current) {
        setRun({ ...data, results: data.results.map((res: RunCaseResult) => ({ ...res, tags: res.tags ?? [] })) });
        setError("");
      }
    } catch (e) {
      if (seq === seqRef.current) {
        setError(e instanceof ApiError ? e.message : "Could not load the results.");
      }
    } finally {
      if (seq === seqRef.current) {
        setLoading(false);
      }
    }
  }, [runId, classification, tags?.join(",")]);

  useEffect(() => {
    const t = setTimeout(() => { load(); }, 300);
    return () => clearTimeout(t);
  }, [load]);

  const setFilter = (next: { classification?: string; tags?: string[] }) => {
    const params = new URLSearchParams();
    if (next.classification) params.set("classification", next.classification);
    if (next.tags?.length) params.set("tags", next.tags.join(","));
    setSearchParams(params);
  };

  if (loading && !run) return <div className="screen"><p>Loading results…</p></div>;

  return (
    <div className="screen">
      <h1>Run results {run && <span className={`run-status status-${run.status.toLowerCase()}`}>{run.status}</span>}</h1>
      <ErrorBanner message={error} onRetry={load} />

      {run && (
        <>
          <div className="run-meta">
            <span>Model: {run.modelId}</span>
            <span>Suite: {run.suiteId}</span>
            <span>Created: {new Date(run.createdAt).toLocaleString()}</span>
            {run.completedAt && <span>Completed: {new Date(run.completedAt).toLocaleString()}</span>}
          </div>

          <SummaryCards summary={run.summary} filtered={Boolean(classification || tags?.length)} />

          <div className="filter-row">
            <label>
              Classification
              <select
                value={classification ?? ""}
                onChange={(e) => setFilter({ classification: e.target.value || undefined, tags })}
              >
                <option value="">All</option>
                {CLASSIFICATIONS.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
            <label>
              Tags (comma-separated)
              <input
                value={tagsParam ?? ""}
                onChange={(e) =>
                  setFilter({ classification, tags: e.target.value.split(",").map((t) => t.trim()).filter(Boolean) })}
                placeholder="e.g. pricing, escalation"
              />
            </label>
            {(classification || tags?.length) && (
              <button onClick={() => setFilter({})}>Clear filters</button>
            )}
          </div>

          {run.results.length === 0 ? (
            <p className="empty">No results match the current filters.</p>
          ) : (
            <ul className="result-list">
              {run.results.map((r: RunCaseResult) => (
                <li key={r.caseId} className="result-item">
                  <div className="result-header">
                    <ClassificationBadge classification={r.classification} />
                    {r.truncated && <span className="truncated-badge" title="One or more outputs were truncated (reached max token limit)">⚠ truncated</span>}
                    {r.tags.length > 0 && r.tags.map((t) => <span key={t} className="tag">{t}</span>)}
                    {r.error && <span className="result-error" title={r.error}>Error — see details</span>}
                  </div>
                  <div className="comparison-grid">
                    <div className="output-col">
                      <h3>Baseline {r.baselineScore != null && <span className="score">{r.baselineScore}/5</span>}</h3>
                      <pre>{r.baselineOutput ?? "—"}</pre>
                      {r.baselineRationale && <p className="rationale">{r.baselineRationale}</p>}
                      {r.baselineLatencyMs != null && <span className="latency">{Math.round(r.baselineLatencyMs)}ms</span>}
                    </div>
                    <div className="output-col">
                      <h3>Candidate {r.candidateScore != null && <span className="score">{r.candidateScore}/5</span>}</h3>
                      <pre>{r.candidateOutput ?? "—"}</pre>
                      {r.candidateRationale && <p className="rationale">{r.candidateRationale}</p>}
                      {r.candidateLatencyMs != null && <span className="latency">{Math.round(r.candidateLatencyMs)}ms</span>}
                    </div>
                  </div>
                  {r.error && <pre className="error-detail">{r.error}</pre>}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
