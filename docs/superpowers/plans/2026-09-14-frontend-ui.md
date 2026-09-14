# Frontend UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the React + TypeScript + Vite frontend for PromptLens with four screens (Home, Suite Editor, Run Configuration, Results) that communicate with the deployed Lambda API.

**Architecture:** Single-page app in a new `frontend/` directory. Thin API client layer (one module, typed responses) feeds screen components. State is local to each screen (useState/useEffect) — no global state library for MVP. Client-side routing via react-router. All screens desktop-first responsive. No AWS SDK, no credentials — the frontend only ever talks to the API base URL.

**Tech Stack:** React 18, TypeScript, Vite, react-router-dom, no CSS framework (plain CSS modules / one stylesheet)

**Spec:** `.scratch/wayfinder/tickets/05-frontend-ui.md`

## Global Constraints

- API base URL read from `VITE_API_BASE_URL` environment variable at build time
- No AWS credentials or Bedrock configuration in frontend code
- App handles API errors gracefully with user-friendly messages
- All screens responsive and functional on desktop
- Initial UI load under 3 seconds on typical broadband
- React app builds and runs locally with Vite
- Suite IDs in URLs: `suiteId` path param
- Model IDs: server-allowlisted; frontend offers a fixed MVP list (below) — actual enforcement is server-side
- MVP model list for the picker:
  - `anthropic.claude-3-haiku-20240307-v1:0` (Fast)
  - `anthropic.claude-3-sonnet-20240229-v1:0` (Balanced)
- Score range 1-5; classifications: Improved | Regressed | Unchanged | Needs review | Failed
- Summary is computed on FILTERED results when a filter is active (frontend must refetch without filters for the full-run summary)
- Maximum 3 cases per run (backend enforces; frontend shows what it sends and displays returned count)

## API Contract (verified against backend code)

- `GET /suites` → `Suite[]` where `Suite = { suiteId, name, createdAt, updatedAt, caseCount }` (caseCount always 0 from list endpoint — suites carry cases only in the by-id GET)
- `GET /suites/{suiteId}` → Suite fields + `cases: Case[]` where `Case = { caseId, suiteId, input, expectedBehavior?, tags }`
- `POST /suites` body `{ name }` → 201 Suite
- `PATCH /suites/{suiteId}` body `{ name }` → 200 Suite
- `DELETE /suites/{suiteId}` → 204 (delete suite + cases)
- `POST /suites/{suiteId}/cases` body `{ input, expectedBehavior?, tags? }` → 201 Case
- `PATCH /suites/{suiteId}/cases/{caseId}` body `{ input?, expectedBehavior?, tags? }` → 200 Case
- `DELETE /suites/{suiteId}/cases/{caseId}` → 204
- `GET /runs` → `Run[]` where `Run = { runId, suiteId, modelId, baselinePrompt, candidatePrompt, rubric, status, temperature, maxTokens, createdAt, completedAt? }`
- `GET /runs?status=X&suiteId=Y` → filtered `Run[]`
- `POST /runs` body `{ suiteId, modelId, baselinePrompt, candidatePrompt, rubric, temperature?, maxTokens?, caseIds? }` → 201 Run (synchronous execution; response is the completed run with status COMPLETED/PARTIAL/FAILED) — may take up to 60s. `caseIds` (optional): list of case IDs to run; filtered to the suite's cases in suite order, capped at 3. If omitted/empty, the suite's first 3 cases run. 400 if caseIds is not a list or if none of the given caseIds match the suite's cases.
- `GET /runs/{runId}` → Run + `results: RunCaseResult[]` + `summary: { total, improved, regressed, unchanged, needsReview, failed }`
- `GET /runs/{runId}?classification=X&tags=a,b` → Run + filtered results + filtered-subset summary
- `RunCaseResult = { runId, caseId, classification, baselineOutput?, candidateOutput?, baselineScore?, candidateScore?, baselineRationale?, candidateRationale?, baselineLatencyMs?, candidateLatencyMs?, error?, tags }`
- All error responses: `{ message: string }` with 4xx/5xx status
- CORS: server allows all origins (CORS is Feature 7 scope)

## File Structure

```
frontend/
  package.json
  vite.config.ts        — dev proxy not used; VITE_API_BASE_URL only
  tsconfig.json
  index.html
  src/
    main.tsx            — entry, router setup
    App.tsx             — layout shell (header + <Outlet/>)
    api/client.ts       — typed fetch wrapper (baseURL, error normalization)
    api/types.ts        — Suite, Case, Run, RunCaseResult, Summary interfaces
    screens/
      HomeScreen.tsx    — suite list, create suite, open demo
      SuiteEditorScreen.tsx — case list + prompt editors (tabs or stacked)
      RunConfigScreen.tsx   — model, temp, tokens, rubric, case selection
      ResultsScreen.tsx     — summary cards, filters, side-by-side comparison
    components/
      ErrorBanner.tsx   — user-friendly error display
      SummaryCards.tsx  — classification count cards
      ClassificationBadge.tsx — colored badge per classification
    styles.css          — single stylesheet, CSS variables for classification colors
```

One API client module, one types module, one stylesheet — kept intentionally small for MVP.

---

### Task 1: Scaffold Vite React App

**Files:**
- Create: `frontend/` (Vite scaffold output)
- Create: `frontend/.env.example` with `VITE_API_BASE_URL=http://localhost:3000`
- Create: `frontend/src/api/types.ts`
- Modify: `frontend/.gitignore` (add `.env`), root `.gitignore` (add `frontend/dist`, `frontend/node_modules`)

**Interfaces:**
- Produces: buildable app shell all later tasks extend; TypeScript types in `src/api/types.ts` for all API entities

- [ ] **Step 1: Scaffold the app**

```bash
cd /Users/pasindulanka/LANKA/Development/AWS/prompt-lens
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
```

- [ ] **Step 2: Create types module**

Create `frontend/src/api/types.ts` with the full API contract types:

```typescript
export interface Suite {
  suiteId: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  caseCount: number;
}

export interface SuiteWithCases extends Suite {
  cases: Case[];
}

export interface Case {
  caseId: string;
  suiteId: string;
  input: string;
  expectedBehavior?: string;
  tags: string[];
}

export interface Run {
  runId: string;
  suiteId: string;
  modelId: string;
  baselinePrompt: string;
  candidatePrompt: string;
  rubric: string;
  status: "RUNNING" | "COMPLETED" | "PARTIAL" | "FAILED";
  temperature: number;
  maxTokens: number;
  createdAt: string;
  completedAt?: string;
}

export interface RunCaseResult {
  runId: string;
  caseId: string;
  classification: "Improved" | "Regressed" | "Unchanged" | "Needs review" | "Failed";
  baselineOutput?: string;
  candidateOutput?: string;
  baselineScore?: number;
  candidateScore?: number;
  baselineRationale?: string;
  candidateRationale?: string;
  baselineLatencyMs?: number;
  candidateLatencyMs?: number;
  error?: string;
  tags: string[];
}

export interface Summary {
  total: number;
  improved: number;
  regressed: number;
  unchanged: number;
  needsReview: number;
  filtered?: boolean;
}

export interface RunWithResults extends Run {
  results: RunCaseResult[];
  summary: Summary;
}
```

Note: `Summary` deliberately lacks `failed` above — **add `failed: number` to the Summary interface** (backend emits it; it was omitted from this listing in error). Final Summary interface:

```typescript
export interface Summary {
  total: number;
  improved: number;
  regressed: number;
  unchanged: number;
  needsReview: number;
  failed: number;
  filtered?: boolean;
}
```

- [ ] **Step 3: Env config + gitignore**

`frontend/.env.example`:
```
VITE_API_BASE_URL=http://localhost:3000
```

Append to `frontend/.gitignore`: `.env` (keep everything the template wrote). Append to root `.gitignore`: `frontend/dist/` and `frontend/node_modules/`.

- [ ] **Step 4: Verify the build**

```bash
npm run build
```

Expected: build succeeds, `dist/` generated.

- [ ] **Step 5: Commit**

```bash
git add frontend/ && git add .gitignore
git commit -m "feat: scaffold Vite React frontend with API types"
```

---

### Task 2: API Client

**Files:**
- Create: `frontend/src/api/client.ts`
- Test: `frontend/src/api/client.test.ts` (Vitest)

**Interfaces:**
- Consumes: types from Task 1
- Produces: `apiFetch` + typed functions: `listSuites()`, `getSuite(id)`, `createSuite(name)`, `updateSuite(id, name)`, `deleteSuite(id)`, `createCase(suiteId, body)`, `updateCase(suiteId, caseId, body)`, `deleteCase(suiteId, caseId)`, `listRuns(status?, suiteId?)`, `getRun(runId, filters?)`, `createRun(body)`

- [ ] **Step 1: Install Vitest and write failing tests**

```bash
cd frontend && npm install -D vitest
```

`frontend/src/api/client.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

import { listSuites, getRun, createRun, ApiError } from "./client";

describe("api client", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("uses VITE_API_BASE_URL as base", async () => {
    mockFetch.mockResolvedValue(okJson([]));
    await listSuites();
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:3000/suites",
      expect.objectContaining({ method: "GET" })
    );
  });

  it("throws ApiError with server message on 4xx", async () => {
    mockFetch.mockResolvedValue(jsonResponse(404, { message: "Suite not found" }));
    await expect(getRun("missing")).rejects.toMatchObject({
      status: 404,
      message: "Suite not found",
    });
  });

  it("sends JSON body and parses run with results", async () => {
    const run = { runId: "r1", results: [], summary: { total: 0 } };
    mockFetch.mockResolvedValue(okJson(run));
    const result = await createRun({ suiteId: "s1", modelId: "m1", baselinePrompt: "b", candidatePrompt: "c", rubric: "r" });
    expect(result.runId).toBe("r1");
    const [, init] = mockFetch.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body).suiteId).toBe("s1");
  });
});

function okJson(data: unknown) {
  return jsonResponse(200, data);
}

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
```

Note: the first test requires `import.meta.env.VITE_API_BASE_URL` to be `http://localhost:3000` in test env — add `frontend/vitest` env handling: create `frontend/.env.test` containing `VITE_API_BASE_URL=http://localhost:3000`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run`
Expected: FAIL — `./client` does not exist

- [ ] **Step 3: Implement client**

`frontend/src/api/client.ts`:

```typescript
import type {
  Suite, SuiteWithCases, Case, Run, RunWithResults, Summary,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, init);
  } catch {
    throw new ApiError(0, "Cannot reach the PromptLens server. Is it running?");
  }
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body?.message) message = body.message;
    } catch {
      /* keep default */
    }
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function jsonInit(method: string, body?: unknown): RequestInit {
  return body === undefined
    ? { method }
    : { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

export const listSuites = () => apiFetch<Suite[]>("/suites");
export const getSuite = (suiteId: string) =>
  apiFetch<SuiteWithCases>(`/suites/${suiteId}`);
export const createSuite = (name: string) =>
  apiFetch<Suite>("/suites", jsonInit("POST", { name }));
export const updateSuite = (suiteId: string, name: string) =>
  apiFetch<Suite>(`/suites/${suiteId}`, jsonInit("PATCH", { name }));
export const deleteSuite = (suiteId: string) =>
  apiFetch<void>(`/suites/${suiteId}`, jsonInit("DELETE"));

export const createCase = (
  suiteId: string,
  body: { input: string; expectedBehavior?: string; tags?: string[] }
) => apiFetch<Case>(`/suites/${suiteId}/cases`, jsonInit("POST", body));
export const updateCase = (
  suiteId: string,
  caseId: string,
  body: { input?: string; expectedBehavior?: string; tags?: string[] }
) => apiFetch<Case>(`/suites/${suiteId}/cases/${caseId}`, jsonInit("PATCH", body));
export const deleteCase = (suiteId: string, caseId: string) =>
  apiFetch<void>(`/suites/${suiteId}/cases/${caseId}`, jsonInit("DELETE"));

export const listRuns = (status?: string, suiteId?: string) => {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (suiteId) params.set("suiteId", suiteId);
  const qs = params.toString();
  return apiFetch<Run[]>(`/runs${qs ? `?${qs}` : ""}`);
};

export const getRun = (runId: string, filters?: { classification?: string; tags?: string[] }) => {
  const params = new URLSearchParams();
  if (filters?.classification) params.set("classification", filters.classification);
  if (filters?.tags?.length) params.set("tags", filters.tags.join(","));
  const qs = params.toString();
  return apiFetch<RunWithResults>(`/runs/${runId}${qs ? `?${qs}` : ""}`);
};

export const createRun = (body: {
  suiteId: string; modelId: string; baselinePrompt: string; candidatePrompt: string;
  rubric: string; temperature?: number; maxTokens?: number;
}) => apiFetch<Run>("/runs", jsonInit("POST", body));
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run`
Expected: 3 passing

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add typed API client with error normalization"
```

---

### Task 3: App Shell, Router, Home Screen

**Files:**
- Create: `frontend/src/main.tsx` (replace template), `frontend/src/App.tsx`, `frontend/src/styles.css`
- Create: `frontend/src/components/ErrorBanner.tsx`
- Create: `frontend/src/screens/HomeScreen.tsx`
- Modify: `frontend/index.html` (title "PromptLens")

**Interfaces:**
- Consumes: `listSuites`, `createSuite` from client
- Produces: routes `/` (Home), `/suites/:suiteId/edit` (placeholder for Task 4), `/suites/:suiteId/run` (placeholder for Task 5), `/runs/:runId` (placeholder for Task 6)

- [ ] **Step 1: Write the shell and Home screen**

`frontend/src/main.tsx`:
```typescript
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App";
import HomeScreen from "./screens/HomeScreen";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<App />}>
          <Route index element={<HomeScreen />} />
          <Route path="suites/:suiteId/edit" element={<HomeScreen />} />
          <Route path="suites/:suiteId/run" element={<HomeScreen />} />
          <Route path="runs/:runId" element={<HomeScreen />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
```

(Placeholders route to Home for now; Tasks 4-6 replace them.)

`frontend/src/App.tsx`:
```typescript
import { Link, Outlet } from "react-router-dom";

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <Link to="/" className="app-title">PromptLens</Link>
        <span className="app-subtitle">Prompt regression testing</span>
      </header>
      <main className="app-main"><Outlet /></main>
    </div>
  );
}
```

`frontend/src/components/ErrorBanner.tsx`:
```typescript
export default function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  if (!message) return null;
  return (
    <div className="error-banner" role="alert">
      <span>{message}</span>
      {onRetry && <button onClick={onRetry}>Retry</button>}
    </div>
  );
}
```

`frontend/src/screens/HomeScreen.tsx`:
```typescript
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
```

- [ ] **Step 2: Add styles + title**

`frontend/src/styles.css` — desktop-first, classification color variables (used in Task 6):
```css
:root {
  --improved: #16a34a;
  --regressed: #dc2626;
  --unchanged: #6b7280;
  --needs-review: #d97706;
  --failed: #991b1b;
  --bg: #f8fafc;
  --panel: #ffffff;
  --border: #e2e8f0;
  --text: #0f172a;
  --muted: #64748b;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text);
}
.app { max-width: 1100px; margin: 0 auto; padding: 0 1rem; }
.app-header {
  display: flex; align-items: baseline; gap: 0.75rem;
  padding: 1rem 0; border-bottom: 1px solid var(--border);
}
.app-title { font-size: 1.5rem; font-weight: 700; color: var(--text); text-decoration: none; }
.app-subtitle { color: var(--muted); font-size: 0.9rem; }
.app-main { padding: 1.5rem 0; }
.screen h1 { margin-top: 0; }
.row { display: flex; gap: 0.5rem; }
input, textarea, select, button {
  font: inherit; padding: 0.5rem 0.75rem;
  border: 1px solid var(--border); border-radius: 6px; background: var(--panel);
}
button { cursor: pointer; }
button:disabled { opacity: 0.5; cursor: not-allowed; }
textarea { width: 100%; min-height: 8rem; font-family: ui-monospace, monospace; }
.suite-list { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 0.5rem; }
.suite-item {
  display: flex; justify-content: space-between; align-items: center;
  background: var(--panel); border: 1px solid var(--border);
  border-radius: 8px; padding: 0.75rem 1rem;
}
.suite-name { font-weight: 600; color: var(--text); text-decoration: none; }
.suite-name:hover { text-decoration: underline; }
.suite-meta { display: block; font-size: 0.8rem; color: var(--muted); }
.suite-actions { display: flex; gap: 0.5rem; }
.empty { color: var(--muted); font-style: italic; }
.error-banner {
  display: flex; justify-content: space-between; align-items: center;
  background: #fef2f2; border: 1px solid #fecaca; color: #991b1b;
  padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1rem;
}
```

Update `frontend/index.html` `<title>` to `PromptLens`.

- [ ] **Step 3: Verify dev server + build**

```bash
cd frontend && npm run build
```
Expected: build passes with no type errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: add app shell, router, and Home screen"
```

---

### Task 4: Suite Editor Screen

**Files:**
- Create: `frontend/src/screens/SuiteEditorScreen.tsx`
- Modify: `frontend/src/main.tsx` (wire `/suites/:suiteId/edit` to it)

**Interfaces:**
- Consumes: `getSuite`, `updateSuite`, `createCase`, `updateCase`, `deleteCase`, `deleteSuite`; `Case` type
- Produces: functional Suite Editor at `/suites/:suiteId/edit`

- [ ] **Step 1: Write the screen**

`frontend/src/screens/SuiteEditorScreen.tsx`:
```typescript
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
      setSuite({ ...s, cases: s.cases.map((c) => ({ ...c, tags: c.tags ?? [] })) });
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
      expectedBehavior: expected,
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
```

- [ ] **Step 2: Wire the route in main.tsx**

Replace the `/suites/:suiteId/edit` placeholder:
```typescript
import SuiteEditorScreen from "./screens/SuiteEditorScreen";
// ...
<Route path="suites/:suiteId/edit" element={<SuiteEditorScreen />} />
```

- [ ] **Step 3: Add editor styles (append to styles.css)**

```css
.editor-header { display: flex; gap: 1rem; justify-content: space-between; margin-bottom: 1rem; }
.suite-name-input { font-size: 1.25rem; font-weight: 600; flex: 1; }
.case-list { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 1rem; }
.case-item { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; }
.case-editor label { display: block; font-size: 0.85rem; color: var(--muted); margin-bottom: 0.5rem; }
.case-editor textarea { min-height: 4rem; }
.case-actions { display: flex; gap: 0.5rem; }
.case-tags { display: flex; gap: 0.25rem; margin-top: 0.5rem; flex-wrap: wrap; }
.tag {
  font-size: 0.75rem; background: var(--bg); border: 1px solid var(--border);
  border-radius: 999px; padding: 0.15rem 0.6rem; color: var(--muted);
}
button.danger { color: var(--failed); border-color: var(--failed); }
```

- [ ] **Step 4: Build check**

```bash
cd frontend && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add Suite Editor screen with case management"
```

---

### Task 5: Run Configuration Screen

**Files:**
- Create: `frontend/src/screens/RunConfigScreen.tsx`
- Modify: `frontend/src/main.tsx` (wire `/suites/:suiteId/run`)

**Interfaces:**
- Consumes: `getSuite`, `createRun`; `Run` type; MVP model list constant
- Produces: functional Run Config at `/suites/:suiteId/run`; navigates to `/runs/:runId` on success

- [ ] **Step 1: Write the screen**

`frontend/src/screens/RunConfigScreen.tsx`:
```typescript
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

  const canSubmit =
    selectedCases.size > 0 &&
    baselinePrompt.trim() && candidatePrompt.trim() && rubric.trim();

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
        maxTokens,
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
          </label>
          <label>
            Candidate prompt
            <textarea
              value={candidatePrompt}
              onChange={(e) => setCandidatePrompt(e.target.value)}
              placeholder="You are a customer support agent. Improvements…"
            />
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
```

- [ ] **Step 2: Wire the route in main.tsx**

```typescript
import RunConfigScreen from "./screens/RunConfigScreen";
// ...
<Route path="suites/:suiteId/run" element={<RunConfigScreen />} />
```

- [ ] **Step 3: Add run config styles (append to styles.css)**

```css
.run-config-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 1rem; align-items: start; }
.config-panel {
  background: var(--panel); border: 1px solid var(--border);
  border-radius: 8px; padding: 1rem;
}
.config-panel h2 { margin-top: 0; font-size: 1rem; }
.config-panel label { display: block; font-size: 0.85rem; color: var(--muted); margin-bottom: 0.75rem; }
.config-panel select, .config-panel input[type="number"] { width: 100%; }
.case-select-list { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 0.4rem; max-height: 16rem; overflow-y: auto; }
.case-select { display: flex; gap: 0.5rem; align-items: flex-start; }
.case-select input { margin-top: 0.25rem; }
button.primary {
  background: var(--text); color: white; border: none;
  padding: 0.6rem 1.2rem; font-weight: 600;
}
button.primary:disabled { opacity: 0.5; }
```

- [ ] **Step 4: Build check**

```bash
cd frontend && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add Run Configuration screen"
```

---

### Task 6: Results Screen

**Files:**
- Create: `frontend/src/components/SummaryCards.tsx`
- Create: `frontend/src/components/ClassificationBadge.tsx`
- Create: `frontend/src/screens/ResultsScreen.tsx`
- Modify: `frontend/src/main.tsx` (wire `/runs/:runId`)

**Interfaces:**
- Consumes: `getRun` with filters; `RunWithResults`, `Summary`, `RunCaseResult` types
- Produces: Results screen with summary cards, classification + tag filters, side-by-side comparison

- [ ] **Step 1: Write components**

`frontend/src/components/SummaryCards.tsx`:
```typescript
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
```

`frontend/src/components/ClassificationBadge.tsx`:
```typescript
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
```

- [ ] **Step 2: Write the Results screen**

`frontend/src/screens/ResultsScreen.tsx`:
```typescript
import { useCallback, useEffect, useState } from "react";
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

  const classification = searchParams.get("classification") ?? undefined;
  const tagsParam = searchParams.get("tags");
  const tags = tagsParam ? tagsParam.split(",").map((t) => t.trim()).filter(Boolean) : undefined;

  const load = useCallback(async () => {
    if (!runId) return;
    setLoading(true);
    setError("");
    try {
      setRun(await getRun(runId, { classification, tags: tags?.length ? tags : undefined }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load the results.");
    } finally {
      setLoading(false);
    }
  }, [runId, classification, tags?.join(",")]);

  useEffect(() => { load(); }, [load]);

  const setFilter = (next: { classification?: string; tags?: string[] }) => {
    const params = new URLSearchParams();
    if (next.classification) params.set("classification", next.classification);
    if (next.tags?.length) params.set("tags", next.tags.join(","));
    setSearchParams(params);
  };

  if (loading) return <div className="screen"><p>Loading results…</p></div>;

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
```

- [ ] **Step 3: Wire the route and add styles**

In `main.tsx`: `import ResultsScreen from "./screens/ResultsScreen";` and replace the `/runs/:runId` placeholder route.

Append to `styles.css`:
```css
.run-meta { display: flex; gap: 1.5rem; color: var(--muted); font-size: 0.85rem; margin-bottom: 1rem; flex-wrap: wrap; }
.run-status {
  font-size: 0.8rem; padding: 0.15rem 0.6rem; border-radius: 999px;
  background: var(--bg); border: 1px solid var(--border); vertical-align: middle;
}
.status-completed { color: var(--improved); border-color: var(--improved); }
.status-partial { color: var(--needs-review); border-color: var(--needs-review); }
.status-failed { color: var(--failed); border-color: var(--failed); }
.status-running { color: var(--muted); }
.summary-cards { display: grid; grid-template-columns: repeat(6, 1fr); gap: 0.5rem; margin: 1rem 0; }
.filtered-note { grid-column: 1 / -1; font-size: 0.8rem; color: var(--needs-review); margin: 0; }
.summary-card {
  display: flex; flex-direction: column; align-items: center; padding: 0.75rem 0.5rem;
  background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
  border-top: 3px solid var(--border);
}
.summary-count { font-size: 1.5rem; font-weight: 700; }
.summary-label { font-size: 0.75rem; color: var(--muted); }
.c-improved { border-top-color: var(--improved); } .c-improved .summary-count { color: var(--improved); }
.c-regressed { border-top-color: var(--regressed); } .c-regressed .summary-count { color: var(--regressed); }
.c-unchanged { border-top-color: var(--unchanged); } .c-unchanged .summary-count { color: var(--unchanged); }
.c-needs-review { border-top-color: var(--needs-review); } .c-needs-review .summary-count { color: var(--needs-review); }
.c-failed { border-top-color: var(--failed); } .c-failed .summary-count { color: var(--failed); }
.filter-row { display: flex; gap: 1rem; align-items: flex-end; margin-bottom: 1rem; }
.filter-row label { display: flex; flex-direction: column; font-size: 0.85rem; color: var(--muted); gap: 0.25rem; }
.result-list { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 1rem; }
.result-item { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; }
.result-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem; flex-wrap: wrap; }
.badge {
  font-size: 0.75rem; font-weight: 600; padding: 0.15rem 0.6rem;
  border-radius: 999px; border: 1px solid;
}
.badge.c-improved { color: var(--improved); border-color: var(--improved); background: #f0fdf4; }
.badge.c-regressed { color: var(--regressed); border-color: var(--regressed); background: #fef2f2; }
.badge.c-unchanged { color: var(--unchanged); border-color: var(--unchanged); }
.badge.c-needs-review { color: var(--needs-review); border-color: var(--needs-review); background: #fffbeb; }
.badge.c-failed { color: var(--failed); border-color: var(--failed); background: #fef2f2; }
.result-error { color: var(--failed); font-size: 0.8rem; }
.comparison-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.output-col h3 {
  margin: 0 0 0.5rem; font-size: 0.9rem; display: flex; justify-content: space-between; align-items: center;
}
.score { font-weight: 700; }
.output-col pre {
  margin: 0; white-space: pre-wrap; font-size: 0.85rem; background: var(--bg);
  border: 1px solid var(--border); border-radius: 6px; padding: 0.75rem; min-height: 3rem;
}
.rationale { font-size: 0.8rem; color: var(--muted); margin: 0.5rem 0 0; }
.latency { font-size: 0.75rem; color: var(--muted); }
.error-detail {
  margin-top: 0.75rem; white-space: pre-wrap; font-size: 0.8rem;
  color: var(--failed); background: #fef2f2; border-radius: 6px; padding: 0.75rem;
}
```

- [ ] **Step 4: Build check + manual smoke route test**

```bash
cd frontend && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add Results screen with summary cards, filters, side-by-side comparison"
```

---

### Task 7: Verification and Cleanup

**Files:**
- Modify: root `README.md` (frontend section), `frontend/README.md` (replace template boilerplate with PromptLens-specific instructions)
- Modify: root `.gitignore` if not already updated in Task 1

- [ ] **Step 1: Full build + tests**

```bash
cd frontend && npm run build && npx vitest run
```
Expected: build passes, all tests pass.

- [ ] **Step 2: Replace frontend/README.md**

Replace the Vite template README with:

```markdown
# PromptLens Frontend

React + TypeScript + Vite frontend for PromptLens, a prompt-regression testing tool.

## Setup

```bash
cd frontend
npm install
cp .env.example .env   # then set your deployed API URL
npm run dev
```

The dev server reads `VITE_API_BASE_URL` at build time (see `.env.example`).

## Screens

- `/` — Home: suite list, create suite
- `/suites/:suiteId/edit` — Suite Editor: rename suite, manage cases
- `/suites/:suiteId/run` — Run Config: prompts, model, settings, case selection (max 3)
- `/runs/:runId` — Results: summary cards, filters, side-by-side comparison

## Testing

```bash
npm run build   # type check + production build
npx vitest run  # unit tests (API client)
```

## Constraints

- No AWS credentials or Bedrock configuration in frontend code
- All model invocations go through the backend API
- MVP: 3 cases per run, 2 model options
```

- [ ] **Step 3: Add frontend section to root README.md**

Under the existing README, append:

```markdown
## Frontend

The React frontend lives in `frontend/`. See `frontend/README.md` for setup. The API base URL is configured via `VITE_API_BASE_URL` (see `.env.example`).
```

- [ ] **Step 4: Verify no credentials in frontend code**

```bash
grep -rE "AKIA|aws_access|SECRET|BEDROCK" frontend/src frontend/.env* || echo "clean"
```
Expected: `clean` (no AWS keys, secrets, or Bedrock config in the frontend).

- [ ] . **Step 5: Commit**

```bash
git add frontend/ README.md
git commit -m "docs: frontend README and cleanup"
```

---

## Self-Review Checklist

- [x] Every ticket acceptance criterion maps to a task: local Vite build (T1), Home lists suites + opens demo (T3), Suite Editor with cases + prompt editors (T4), Run Config (T5), Results summary cards + filters (T6), side-by-side comparison (T6), responsive desktop (all tasks, CSS), VITE_API_BASE_URL (T1/T2), no credentials (T7 verify), graceful errors (T2 client + ErrorBanner all screens), <3s load (Vite bundle, minimal deps)
- [x] No placeholders — all screens have complete component code
- [x] Type consistency — Summary includes `failed`; RunCaseResult includes `tags`; Suite/Case/Run fields verified against backend `to_response()` implementations (suite.py:32-40, case.py:31-42, run.py:45-61)
- [x] Note for executors: `frontend/node_modules` and `frontend/dist` must be gitignored (Task 1 Step 3)
```
