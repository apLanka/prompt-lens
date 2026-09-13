import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import SuiteEditorScreen from "./SuiteEditorScreen";
import type { SuiteWithCases } from "../api/types";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    getSuite: vi.fn(),
    updateSuite: vi.fn(),
    createCase: vi.fn(),
    updateCase: vi.fn(),
    deleteCase: vi.fn(),
    deleteSuite: vi.fn(),
  };
});

const suiteWithoutTags = {
  suiteId: "s1",
  name: "Customer-support replies",
  createdAt: "2026-09-14T00:00:00Z",
  updatedAt: "2026-09-14T00:00:00Z",
  caseCount: 1,
  cases: [
    {
      caseId: "c1",
      suiteId: "s1",
      input: "Refund request for late delivery",
      // tags intentionally omitted: the backend omits empty lists from JSON
    },
  ],
} as unknown as SuiteWithCases;

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={["/suites/s1/edit"]}>
      <Routes>
        <Route path="suites/:suiteId/edit" element={<SuiteEditorScreen />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("SuiteEditorScreen", () => {
  it("renders a case whose tags field is missing from the API response", async () => {
    const { getSuite } = await import("../api/client");
    vi.mocked(getSuite).mockResolvedValue(suiteWithoutTags);

    let rendered: ReturnType<typeof renderScreen>;
    expect(() => {
      rendered = renderScreen();
    }).not.toThrow();

    await waitFor(() => {
      expect(screen.getByText("Refund request for late delivery")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Save case" })).toBeInTheDocument();
    rendered!.unmount();
  });
});
