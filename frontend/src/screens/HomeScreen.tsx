import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSuites, createSuite, ApiError } from "../api/client";
import type { Suite } from "../api/types";
import ErrorBanner from "../components/ErrorBanner";

export default function HomeScreen() {
  const [suites, setSuites] = useState<Suite[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setSuites(await listSuites());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong loading suites.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      await createSuite(newName.trim());
      setNewName("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the suite.");
    }
  };

  return (
    <div className="screen">
      <h1>Suites</h1>
      <ErrorBanner message={error} onRetry={load} />
      <form className="row" onSubmit={handleCreate}>
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New suite name…"
          aria-label="New suite name"
        />
        <button type="submit" disabled={!newName.trim()}>Create suite</button>
      </form>
      {loading ? (
        <p>Loading suites…</p>
      ) : suites.length === 0 ? (
        <p className="empty">No suites yet. Create one above to get started.</p>
      ) : (
        <ul className="suite-list">
          {suites.map((s) => (
            <li key={s.suiteId} className="suite-item">
              <div>
                <Link to={`/suites/${s.suiteId}/edit`} className="suite-name">{s.name}</Link>
                <span className="suite-meta">Created {new Date(s.createdAt).toLocaleDateString()}</span>
              </div>
              <div className="suite-actions">
                <Link to={`/suites/${s.suiteId}/run`}><button>New run</button></Link>
                <Link to={`/suites/${s.suiteId}/edit`}><button>Open</button></Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
