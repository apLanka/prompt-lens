import type {
  Suite, SuiteWithCases, Case, Run, RunWithResults,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, init ?? { method: "GET" });
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
