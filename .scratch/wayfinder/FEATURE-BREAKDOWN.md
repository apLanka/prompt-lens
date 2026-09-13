# PromptLens MVP - Feature Breakdown

## Overview

This document breaks down the PromptLens MVP into isolated, sequential features (epics) with clear scope, dependencies, and acceptance criteria.

**Total Features:** 7
**Estimated Sequence:** Infrastructure → Core Logic → UI → Polish → Deploy

---

## Feature 1: Infrastructure Scaffold

**Scope & Boundary:**
- **Owns:** DynamoDB table, IAM role, API Gateway, Lambda skeleton, SAM/CDK templates
- **Delegates:** Bedrock model config (AWS console), Amplify setup (ticket 07), app logic (tickets 02-06)

**Core Entities / Data Models:**
- DynamoDB Table: `PromptLens` with PK/SK
- IAM Role: Lambda execution role

**Technical Dependencies & Pre-requisites:**
- AWS CLI configured
- SAM CLI or CDK installed
- Bedrock model access enabled

**Acceptance Criteria:**
- [ ] DynamoDB table created with PK and SK
- [ ] IAM role created with least-privilege permissions
- [ ] API Gateway HTTP API deployed with CORS
- [ ] Lambda function deployed and responding to health check
- [ ] SAM/CDK template deploys entire stack
- [ ] No hardcoded credentials

---

## Feature 2: Suite Management

**Scope & Boundary:**
- **Owns:** Suite CRUD, Case CRUD, DynamoDB operations, seed data, API endpoints
- **Delegates:** Run execution (ticket 03), Frontend UI (ticket 05), Auth (post-MVP)

**Core Entities / Data Models:**
- Suite: PK=`SUITE#{suiteId}`, SK=`META`
- Case: PK=`SUITE#{suiteId}`, SK=`CASE#{caseId}`

**Technical Dependencies & Pre-requisites:**
- 01-infrastructure-scaffold completed
- DynamoDB table available
- Lambda with DynamoDB permissions

**Acceptance Criteria:**
- [ ] POST /suites creates suite
- [ ] GET /suites lists all suites
- [ ] GET /suites/{suiteId} returns suite with cases
- [ ] PATCH /suites/{suiteId} renames suite
- [ ] DELETE /suites/{suiteId} deletes suite and cases
- [ ] POST /suites/{suiteId}/cases adds case
- [ ] PATCH /suites/{suiteId}/cases/{caseId} edits case
- [ ] DELETE /suites/{suiteId}/cases/{caseId} deletes case
- [ ] Seed data creates demo suite with 3+ cases
- [ ] Cases cannot exist without Suite

---

## Feature 3: Run Execution

**Scope & Boundary:**
- **Owns:** Run creation, Bedrock invocation, evaluator invocation, result storage, synchronous orchestration
- **Delegates:** Suite/Case mgmt (ticket 02), Frontend UI (ticket 05), Results display (ticket 04)

**Core Entities / Data Models:**
- Run: PK=`RUN#{runId}`, SK=`META`
- Run-Case Result: PK=`RUN#{runId}`, SK=`CASE#{caseId}`
- Evaluator Response: {score, confidence, rationale, violations}

**Technical Dependencies & Pre-requisites:**
- 02-suite-management completed
- Bedrock model access configured
- Lambda with Bedrock permissions

**Acceptance Criteria:**
- [ ] POST /runs creates and executes run
- [ ] Processes up to 3 cases synchronously
- [ ] Both prompts execute against same cases
- [ ] Bedrock evaluator scores 1-5
- [ ] Evaluator response validated against schema
- [ ] Scores clamped to 1-5 range
- [ ] Malformed responses marked "Needs review"
- [ ] Run status: RUNNING → COMPLETED | PARTIAL | FAILED
- [ ] Individual failures don't fail entire run
- [ ] Results include all required fields
- [ ] Estimated invocation count shown

---

## Feature 4: Results & Review

**Scope & Boundary:**
- **Owns:** Results retrieval, summary cards, side-by-side comparison, status/tag filtering
- **Delegates:** Run execution (ticket 03), Frontend UI (ticket 05), Run config UI (ticket 05)

**Core Entities / Data Models:**
- Classification: Improved | Regressed | Unchanged | Needs review | Failed
- Run-Case Result fields: outputs, scores, rationales, latency, classification

**Technical Dependencies & Pre-requisites:**
- 03-run-execution completed
- Run-Case Results in DynamoDB
- GET /runs/{runId} endpoint

**Acceptance Criteria:**
- [ ] GET /runs/{runId} returns run with results
- [ ] Summary cards show counts per classification
- [ ] Side-by-side baseline/candidate comparison
- [ ] Filter by status (Improved, Regressed, etc.)
- [ ] Filter by test-case tags
- [ ] Results persist after browser refresh
- [ ] Partial results shown for PARTIAL runs
- [ ] Error cases show user-safe messages

---

## Feature 5: Frontend UI

**Scope & Boundary:**
- **Owns:** React app, routing, all screens, API client, env var config
- **Delegates:** Backend API (tickets 02-04), Amplify hosting (ticket 07), Bedrock config (server-side)

**Core Entities / Data Models:**
- Frontend State: suites, current suite, run config, results
- API Contract: all endpoints from tickets 02-04

**Technical Dependencies & Pre-requisites:**
- 02-suite-management completed
- 04-results-review completed
- Node.js/npm installed
- Amplify CLI configured

**Acceptance Criteria:**
- [ ] React app builds and runs locally
- [ ] Home screen lists suites, opens demo
- [ ] Suite Editor with case list and prompt editors
- [ ] Run Config screen with model, temp, tokens, rubric, cases
- [ ] Results screen with summary, filters, comparison
- [ ] Responsive on desktop
- [ ] API URL from VITE_API_BASE_URL
- [ ] No AWS credentials in frontend
- [ ] Graceful error handling
- [ ] UI loads under 3 seconds

---

## Feature 6: Safety & Guardrails

**Scope & Boundary:**
- **Owns:** Request validation, case/prompt/token limits, CloudWatch logging, invocation estimate
- **Delegates:** Bedrock access controls (server-side), Auth (post-MVP), Cost dashboards (post-MVP)

**Core Entities / Data Models:**
- Validation Rules: max 20 cases, prompt/input length limits, output token config
- CloudWatch Log: runId, caseId, sizes, duration, status, errors

**Technical Dependencies & Pre-requisites:**
- 03-run-execution completed
- Lambda with CloudWatch permissions
- API Gateway validation

**Acceptance Criteria:**
- [ ] API Gateway validates payload
- [ ] Lambda validates case count ≤ 20
- [ ] Lambda validates prompt/input length
- [ ] Lambda validates output tokens
- [ ] Invocation count shown before run
- [ ] CloudWatch logs structured metadata
- [ ] No full prompts/outputs in logs
- [ ] Clear validation error messages
- [ ] Oversized output truncated
- [ ] DynamoDB items under 400KB

---

## Feature 7: Deployment & Polish

**Scope & Boundary:**
- **Owns:** Amplify hosting, CORS config, UI polish, error handling, documentation, screenshots
- **Delegates:** Backend infra (ticket 01), App logic (tickets 02-06), Auth (post-MVP)

**Core Entities / Data Models:**
- Deployment Config: Amplify app, env vars, CORS
- Documentation: README, architecture, screenshots

**Technical Dependencies & Pre-requisites:**
- 05-frontend-ui completed
- 06-safety-guardrails completed
- GitHub repo connected to Amplify

**Acceptance Criteria:**
- [ ] Public Amplify URL loads
- [ ] App matches local development
- [ ] CORS restricted to Amplify domain
- [ ] Results page polished
- [ ] Error handling comprehensive
- [ ] User-friendly error messages
- [ ] Technical errors in CloudWatch
- [ ] Architecture diagram captured
- [ ] Demo screenshots captured
- [ ] README with deployment instructions
- [ ] README with env var documentation
- [ ] README with cost/safety guidance
- [ ] Seeded demo works end-to-end

---

## Execution Order

```
01 Infrastructure Scaffold
    ↓
02 Suite Management
    ↓
03 Run Execution
    ↓
04 Results & Review
    ↓
05 Frontend UI (depends on 02, 04)
    ↓
06 Safety & Guardrails (depends on 03)
    ↓
07 Deployment & Polish (depends on 05, 06)
```

## Parallelization Opportunities

- Tickets 02 and 06 can be developed in parallel (both depend on 03, but not on each other)
- Ticket 05 can start as soon as API contracts are defined (before full backend completion)
- Documentation can be written incrementally throughout development
