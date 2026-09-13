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
    const error = await getRun("missing").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
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
