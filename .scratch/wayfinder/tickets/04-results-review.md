# 04: Results & Review

**What to build:** Implement the results display with run-level summary cards, case-level side-by-side comparison, status filters, and tag-based filtering. Show baseline/candidate outputs, scores, and evaluator rationales.

**Blocked by:** 03-run-execution

**Status:** ready-for-agent

## Scope & Boundary

**Owns:**
- Run results retrieval and display
- Run-level summary (counts of Improved, Regressed, Unchanged, Needs review, Failed)
- Case-level side-by-side comparison view
- Status filtering (filter by classification type)
- Tag-based filtering
- Results persistence (viewable after browser refresh)

**Delegates:**
- Run execution (handled in ticket 03)
- Frontend UI shell (handled in ticket 05)
- Run configuration UI (handled in ticket 05)

## Core Entities / Data Models

**Run-Case Result:**
- baselineOutput: string
- candidateOutput: string
- scores: { baseline: number, candidate: number }
- rationales: { baseline: string, candidate: string }
- latency: { baseline: number, candidate: number }
- classification: "Improved" | "Regressed" | "Unchanged" | "Needs review" | "Failed"

**Classification Logic:**
- Improved: candidateScore > baselineScore
- Regressed: candidateScore < baselineScore
- Unchanged: scores equal AND evaluator confidence acceptable
- Needs review: evaluator error, low confidence, truncated output, or material-difference rules trigger
- Failed: generation or storage fails after retries

## Technical Dependencies & Pre-requisites

- 03-run-execution completed
- Run-Case Results stored in DynamoDB
- GET /runs/{runId} endpoint available

## Acceptance Criteria

- [ ] GET /runs/{runId} returns run metadata and all case results
- [ ] Results page shows run-level summary cards with counts per classification
- [ ] Each case shows baseline and candidate outputs side-by-side
- [ ] Each case shows scores and evaluator rationales
- [ ] User can filter results by status (Improved, Regressed, etc.)
- [ ] User can filter results by test-case tags
- [ ] Results remain viewable after browser refresh (stored in DynamoDB)
- [ ] Partial results displayed if run is PARTIAL status
- [ ] Error cases show user-safe error message with technical detail in CloudWatch
