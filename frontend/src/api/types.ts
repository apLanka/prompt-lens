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
  invocations?: number;
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
  truncated: boolean;
}

export interface Summary {
  total: number;
  improved: number;
  regressed: number;
  unchanged: number;
  needsReview: number;
  failed: number;
  filtered?: boolean;
}

export interface RunWithResults extends Run {
  results: RunCaseResult[];
  summary: Summary;
}
