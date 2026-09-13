# 03: Run Execution

**What to build:** Implement the comparison run orchestration that takes baseline and candidate prompts, executes them against selected cases using Bedrock, and stores results. Includes synchronous processing for up to 3 cases.

**Blocked by:** 02-suite-management

**Status:** ready-for-agent

## Scope & Boundary

**Owns:**
- Run creation and configuration
- Bedrock invocation for baseline and candidate prompts
- Bedrock evaluator invocation with strict JSON schema
- Run-Case Result storage and classification
- Synchronous execution orchestration (up to 3 cases)

**Delegates:**
- Suite and Case management (handled in ticket 02)
- Frontend UI for run configuration (handled in ticket 05)
- Results display (handled in ticket 04)
- Asynchronous execution (post-MVP)

## Core Entities / Data Models

**Run:**
- PK = `RUN#{runId}`
- SK = `META`
- Fields: suiteId, modelId, prompts (baseline, candidate), rubric, settings, status, createdAt

**Run-Case Result:**
- PK = `RUN#{runId}`
- SK = `CASE#{caseId}`
- Fields: baselineOutput, candidateOutput, scores, rationales, latency, classification, error

**Evaluator Response Schema:**
```json
{
  "score": 1-5,
  "confidence": "high|medium|low",
  "rationale": "...",
  "violations": ["..."]
}
```

## Technical Dependencies & Pre-requisites

- 02-suite-management completed
- Bedrock model access configured in AWS region
- Lambda function with Bedrock invocation permissions

## Acceptance Criteria

- [ ] POST /runs creates a new run and executes it
- [ ] Run processes up to 3 cases synchronously
- [ ] Both baseline and candidate prompts execute against same cases
- [ ] Bedrock evaluator scores each output with 1-5 scale
- [ ] Evaluator response validated against strict JSON schema
- [ ] Scores clamped to 1-5 range; out-of-range values normalized
- [ ] Malformed evaluator responses marked as "Needs review"
- [ ] Run status progresses: RUNNING → COMPLETED | PARTIAL | FAILED
- [ ] Individual case failures don't fail entire run
- [ ] Results include baselineOutput, candidateOutput, scores, rationales, latency, classification
- [ ] Estimated invocation count shown before run starts
