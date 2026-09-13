import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  getSuite, updateSuite, createCase, updateCase, deleteCase, deleteSuite, ApiError,
} from "../api/client";
import type { Case, SuiteWithCases } from "../api/types";
import ErrorBanner from "../components/ErrorBanner";

export default function SuiteEditorScreen() {
  const { suiteId } = useParams<{ suiteId: string }>();
  const navigate = useNavigate();
  const [suite, setSuite] = useState<SuiteWithCases | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [newCaseInput, setNewCaseInput] = useState("");
  const [nameDraft, setNameDraft] = useState("");

  const load = async () => {
    if (!suiteId) return;
    setLoading(true);
    setError("");
    try {
      const s = await getSuite(suiteId);
      setSuite(s);
      setNameDraft(s.name);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load the suite.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [suiteId]);

  if (!suiteId) return null;

  const renameSuite = async () => {
    if (!nameDraft.trim() || nameDraft === suite?.name) return;
    try {
      await updateSuite(suiteId, nameDraft.trim());
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not rename the suite.");
    }
  };

  const addCase = async () => {
    if (!newCaseInput.trim()) return;
    try {
      await createCase(suiteId, { input: newCaseInput.trim() });
      setNewCaseInput("");
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not add the case.");
    }
  };

  const patchCase = async (caseId: string, body: Partial<Pick<Case, "input" | "expectedBehavior" | "tags">>) => {
    try {
      await updateCase(suiteId, caseId, body);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not update the case.");
    }
  };

  const removeCase = async (caseId: string) => {
    try {
      await deleteCase(suiteId, caseId);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not delete the case.");
    }
  };

  const removeSuite = async () => {
    if (!confirm("Delete this suite and all its cases?")) return;
    try {
      await deleteSuite(suiteId);
      navigate("/");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not delete the suite.");
    }
  };

  if (loading) return <div className="screen"><p>Loading suite…</p></div>;

  return (
    <div className="screen">
      <div className="editor-header">
        <input
          value={nameDraft}
          onChange={(e) => setNameDraft(e.target.value)}
          onBlur={renameSuite}
          aria-label="Suite name"
          className="suite-name-input"
        />
        <div className="suite-actions">
          <Link to={`/suites/${suiteId}/run`}><button>New run</button></Link>
          <button onClick={removeSuite} className="danger">Delete suite</button>
        </div>
      </div>
      <ErrorBanner message={error} onRetry={load} />

      <h2>Cases</h2>
      {suite?.cases.length === 0 && <p className="empty">No cases yet. Add one below.</p>}
      <ul className="case-list">
        {suite?.cases.map((c) => (
          <li key={c.caseId} className="case-item">
            <CaseRow caseData={c} onPatch={patchCase} onDelete={removeCase} />
          </li>
        ))}
      </ul>

      <div className="row">
        <input
          value={newCaseInput}
          onChange={(e) => setNewCaseInput(e.target.value)}
          placeholder="New case input…"
          aria-label="New case input"
        />
        <button onClick={addCase} disabled={!newCaseInput.trim()}>Add case</button>
      </div>
    </div>
  );
}

function CaseRow({
  caseData, onPatch, onDelete,
}: {
  caseData: Case;
  onPatch: (caseId: string, body: Partial<Pick<Case, "input" | "expectedBehavior" | "tags">>) => void;
  onDelete: (caseId: string) => void;
}) {
  const [input, setInput] = useState(caseData.input);
  const [expected, setExpected] = useState(caseData.expectedBehavior ?? "");

  useEffect(() => {
    setInput(caseData.input);
    setExpected(caseData.expectedBehavior ?? "");
  }, [caseData]);

  const save = () =>
    onPatch(caseData.caseId, {
      input,
      expectedBehavior: expected || undefined,
      tags: caseData.tags,
    });

  return (
    <div className="case-editor">
      <label>
        Input
        <textarea value={input} onChange={(e) => setInput(e.target.value)} />
      </label>
      <label>
        Expected behavior
        <textarea value={expected} onChange={(e) => setExpected(e.target.value)} />
      </label>
      <div className="case-actions">
        <button onClick={save}>Save case</button>
        <button onClick={() => onDelete(caseData.caseId)} className="danger">Delete</button>
      </div>
      {caseData.tags.length > 0 && (
        <div className="case-tags">
          {caseData.tags.map((t) => <span key={t} className="tag">{t}</span>)}
        </div>
      )}
    </div>
  );
}
