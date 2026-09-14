import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ResultsScreen from "./ResultsScreen";
import type { RunWithResults } from "../api/types";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    getRun: vi.fn(),
  };
});

const runWithoutTags = {
  runId: "r1",
  suiteId: "s1",
  modelId: "anthropic.claude-sonnet",
  baselinePrompt: "baseline",
  candidatePrompt: "candidate",
  rubric: "rubric",
  status: "COMPLETED",
  temperature: 0.7,
  maxTokens: 1024,
  createdAt: "2026-09-14T00:00:00Z",
  results: [
    {
      runId: "r1",
      caseId: "c1",
      classification: "Improved",
      baselineOutput: "base out",
      candidateOutput: "cand out",
      baselineScore: 3,
      candidateScore: 4,
      // tags intentionally omitted: the backend omits empty lists from JSON
    },
  ],
  summary: { total: 1, improved: 1, regressed: 0, unchanged: 0, needsReview: 0, failed: 0 },
} as unknown as RunWithResults;

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={["/runs/r1"]}>
      <Routes>
        <Route path="runs/:runId" element={<ResultsScreen />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ResultsScreen", () => {
  it("renders a result whose tags field is missing from the API response", async () => {
    const { getRun } = await import("../api/client");
    vi.mocked(getRun).mockResolvedValue(runWithoutTags);

    let rendered: ReturnType<typeof renderScreen>;
    expect(() => {
      rendered = renderScreen();
    }).not.toThrow();

    await waitFor(() => {
      expect(screen.getByText("base out")).toBeInTheDocument();
    });
    expect(screen.getByText("cand out")).toBeInTheDocument();
    expect(screen.getByText("3/5")).toBeInTheDocument();
    expect(screen.getByText("4/5")).toBeInTheDocument();
    rendered!.unmount();
  });
});
