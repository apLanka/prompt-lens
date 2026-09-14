import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getSuite, createRun, ApiError } from "../api/client";
import type { Case, SuiteWithCases } from "../api/types";
import ErrorBanner from "../components/ErrorBanner";

const MODELS = [
  { id: "anthropic.claude-3-haiku-20240307-v1:0", label: "Claude 3 Haiku (Fast)" },
  { id: "anthropic.claude-3-sonnet-20240229-v1:0", label: "Claude 3 Sonnet (Balanced)" },
];

const DEFAULT_RUBRIC =
  "Rate how well the response addresses the customer's issue: empathy, accuracy, and actionability. 5 = excellent, 1 = poor.";

const MAX_PROMPT_LENGTH = 10000;

export default function RunConfigScreen() {
  const { suiteId } = useParams<{ suiteId: string }>();
  const navigate = useNavigate();
  const [suite, setSuite] = useState<SuiteWithCases | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const [modelId, setModelId] = useState(MODELS[0].id);
  const [baselinePrompt, setBaselinePrompt] = useState("");
  const [candidatePrompt, setCandidatePrompt] = useState("");
  const [rubric, setRubric] = useState(DEFAULT_RUBRIC);
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(1024);
  const [selectedCases, setSelectedCases] = useState<Set<string>>(new Set());

  useEffect(() => {
    (async () => {
      if (!suiteId) return;
      try {
        const s = await getSuite(suiteId);
        setSuite(s);
        setSelectedCases(new Set(s.cases.slice(0, 3).map((c) => c.caseId)));
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Could not load the suite.");
      } finally {
        setLoading(false);
      }
    })();
  }, [suiteId]);

  if (loading) return <div className="screen"><p>Loading suite…</p></div>;
  if (!suite) return <div className="screen"><ErrorBanner message={error || "Suite not found."} /></div>;

  const toggleCase = (caseId: string) => {
    const next = new Set(selectedCases);
    if (next.has(caseId)) next.delete(caseId);
    else if (next.size < 3) next.add(caseId);  // MVP cap: 3 cases per run
    setSelectedCases(next);
  };

  const baselineTooLong = baselinePrompt.length > MAX_PROMPT_LENGTH;
  const candidateTooLong = candidatePrompt.length > MAX_PROMPT_LENGTH;

  const canSubmit =
    selectedCases.size > 0 &&
    baselinePrompt.trim() && candidatePrompt.trim() && rubric.trim() &&
    !baselineTooLong && !candidateTooLong;

  const launch = async () => {
    if (!suiteId || !canSubmit) return;
    setSubmitting(true);
    setError("");
    try {
      const run = await createRun({
        suiteId,
        modelId,
        baselinePrompt,
        candidatePrompt,
        rubric,
        temperature,
        maxTokens: Math.min(4096, Math.max(256, maxTokens || 1024)),
        caseIds: Array.from(selectedCases),
      });
      navigate(`/runs/${run.runId}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not start the run.");
      setSubmitting(false);
    }
  };

  return (
    <div className="screen">
      <h1>New run — {suite.name}</h1>
      <ErrorBanner message={error} />
      {(baselineTooLong || candidateTooLong) && (
        <div className="validation-error">
          Prompts must be under {MAX_PROMPT_LENGTH.toLocaleString()} characters.
          {baselineTooLong && ` Baseline is ${baselinePrompt.length.toLocaleString()}.`}
          {candidateTooLong && ` Candidate is ${candidatePrompt.length.toLocaleString()}.`}
        </div>
      )}
      <p><Link to={`/suites/${suiteId}/edit`}>← Back to suite</Link></p>

      <div className="run-config-grid">
        <div className="config-panel">
          <h2>Prompts</h2>
          <label>
            Baseline prompt
            <textarea
              value={baselinePrompt}
              onChange={(e) => setBaselinePrompt(e.target.value)}
              placeholder="You are a customer support agent…"
            />
            <small className={baselineTooLong ? "char-over" : ""}>
              {baselinePrompt.length.toLocaleString()} / {MAX_PROMPT_LENGTH.toLocaleString()} characters
            </small>
          </label>
          <label>
            Candidate prompt
            <textarea
              value={candidatePrompt}
              onChange={(e) => setCandidatePrompt(e.target.value)}
              placeholder="You are a customer support agent. Improvements…"
            />
            <small className={candidateTooLong ? "char-over" : ""}>
              {candidatePrompt.length.toLocaleString()} / {MAX_PROMPT_LENGTH.toLocaleString()} characters
            </small>
          </label>
        </div>

        <div className="config-panel">
          <h2>Settings</h2>
          <label>
            Model
            <select value={modelId} onChange={(e) => setModelId(e.target.value)}>
              {MODELS.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
            </select>
          </label>
          <label>
            Temperature: {temperature.toFixed(1)}
            <input
              type="range" min="0" max="1" step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(Number(e.target.value))}
            />
          </label>
          <label>
            Max output tokens
            <input
              type="number" min="256" max="4096" step="256"
              value={maxTokens}
              onChange={(e) => setMaxTokens(Number(e.target.value))}
            />
          </label>
          <label>
            Rubric
            <textarea value={rubric} onChange={(e) => setRubric(e.target.value)} />
          </label>
        </div>

        <div className="config-panel">
          <h2>Cases ({selectedCases.size}/3 selected)</h2>
          {suite.cases.length === 0 && (
            <p className="empty">This suite has no cases. <Link to={`/suites/${suiteId}/edit`}>Add some first.</Link></p>
          )}
          <ul className="case-select-list">
            {suite.cases.map((c: Case) => (
              <li key={c.caseId}>
                <label className="case-select">
                  <input
                    type="checkbox"
                    checked={selectedCases.has(c.caseId)}
                    onChange={() => toggleCase(c.caseId)}
                    disabled={!selectedCases.has(c.caseId) && selectedCases.size >= 3}
                  />
                  <span>{c.input.slice(0, 80)}{c.input.length > 80 ? "…" : ""}</span>
                </label>
              </li>
            ))}
          </ul>
          <button className="primary" onClick={launch} disabled={!canSubmit || submitting}>
            {submitting ? "Running… (up to 60s)" : "Run comparison"}
          </button>
        </div>
      </div>
    </div>
  );
}
