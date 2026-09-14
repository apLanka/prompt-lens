# PromptLens — Architecture

A comprehensive architectural reference for the PromptLens prompt-regression testing workspace.

## Table of Contents

- [System Overview](#system-overview)
- [DynamoDB Design](#dynamodb-design)
- [Lambda Handler](#lambda-handler)
- [API Endpoints](#api-endpoints)
- [Data Models](#data-models)
- [Bedrock Integration](#bedrock-integration)
- [Frontend Architecture](#frontend-architecture)
- [Security Model](#security-model)
- [Cost Profile](#cost-profile)
- [Key Design Decisions](#key-design-decisions)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            AWS Cloud                                     │
│                                                                         │
│  ┌──────────────┐     ┌───────────────────────────────────────────────┐  │
│  │   Amplify    │     │              API Gateway (REST)               │  │
│  │   (React +   │────▶│  Stage: Prod                                  │  │
│  │    Vite)     │◀────│  CORS: AllowOrigin = ${AmplifyDomain}         │  │
│  │              │     │  Methods: GET, POST, PUT, DELETE, OPTIONS      │  │
│  └──────────────┘     └──────────────────────┬────────────────────────┘  │
│                                              │                           │
│                                      ┌───────▼────────┐                  │
│                                      │     Lambda      │                  │
│                                      │   (Python 3.11) │                  │
│                                      │   256MB / 30s   │                  │
│                                      └───────┬────────┘                  │
│                                              │                           │
│                       ┌──────────────────────┼──────────────────────┐    │
│                       │                      │                      │    │
│               ┌───────▼──────┐      ┌───────▼──────┐      ┌───────▼──────┐
│               │   DynamoDB   │      │   Bedrock    │      │  CloudWatch  │
│               │  PAY_PER_REQ │      │  InvokeModel │      │  Log Group   │
│               │  Single Table│      │  (server-    │      │  Structured  │
│               │  + SK-index  │      │   side only) │      │  metadata    │
│               │  GSI         │      │              │      │  only        │
│               └──────────────┘      └──────────────┘      └──────────────┘
```

**Request lifecycle:**

1. Frontend sends request to API Gateway (`VITE_API_BASE_URL`)
2. API Gateway routes to Lambda via `{proxy+}` catch-all
3. Lambda handler dispatches to the appropriate route handler
4. Route handler validates input, interacts with DynamoDB/Bedrock
5. Response returned through API Gateway to frontend
6. Structured logs written to CloudWatch (no raw prompts/outputs)

---

## DynamoDB Design

Single-table design using `PK` (String) and `SK` (String) keys, with an `SK-index` GSI for reverse lookups.

### Key Patterns

| Entity | PK | SK | Example |
|--------|----|----|---------|
| Suite | `SUITE#<suiteId>` | `METADATA` | `SUITE#abc123 · METADATA` |
| Case | `SUITE#<suiteId>` | `CASE#<caseId>` | `SUITE#abc123 · CASE#def456` |
| Run | `RUN#<runId>` | `METADATA` | `RUN#xyz789 · METADATA` |
| Run-Case Result | `RUN#<runId>` | `RESULT#<caseId>` | `RUN#xyz789 · RESULT#def456` |

### Access Patterns

| Operation | Key(s) | Notes |
|-----------|--------|-------|
| List suites | `PK = SUITE#*, SK = METADATA` | Scan or prefix query |
| Get suite + cases | `PK = SUITE#<id>` | Query returns METADATA + all CASE# items |
| List runs | `PK = RUN#*, SK = METADATA` | Filter by status/suiteId in-memory |
| Get run + results | `PK = RUN#<id>` | Query returns METADATA + all RESULT# items |
| Get results by classification | `SK-index: SK = RESULT#*, PK = RUN#<id>` | GSI query with filter |

### GSI: SK-index

```
IndexName: SK-index
KeySchema: SK (HASH), PK (RANGE)
Projection: ALL
```

Enables querying all results across runs by classification, or all items of a given SK type.

### Item Size Limits

- DynamoDB max item size: 400KB
- `MAX_STRING_ATTRIBUTE_SIZE`: 350,000 characters (safe margin)
- `MAX_TOKENS_PER_CASE`: 3,000 (prevents oversized outputs)
- Bedrock outputs exceeding this are truncated with `... [truncated]`

---

## Lambda Handler

Single Lambda function (`PromptLensApi`) handles all routes via a catch-all `{proxy+}` event.

### Entry Point

```
backend/src/handlers/api/__init__.py  →  handler(event, context)
```

### Route Dispatch

```
handler(event)
  ├── GET/POST /suites       → routes/suites.py
  ├── GET/PUT/DELETE /suites/{suiteId}  → routes/suites.py
  ├── GET/POST /suites/{suiteId}/cases  → routes/cases.py
  ├── PUT/DELETE /suites/{suiteId}/cases/{caseId}  → routes/cases.py
  ├── GET/POST /runs         → routes/runs.py
  ├── GET/DELETE /runs/{runId}  → routes/runs.py
  └── GET /health            → health response
```

### Configuration

| Setting | Value |
|---------|-------|
| Runtime | Python 3.11 |
| Memory | 256 MB |
| Timeout | 30 seconds |
| Tracing | Active (X-Ray) |
| Env vars | `TABLE_NAME` (from CloudFormation) |

---

## API Endpoints

### Suites

| Method | Path | Description | Status |
|--------|------|-------------|--------|
| `GET` | `/suites` | List all suites | 200 |
| `POST` | `/suites` | Create a suite | 201 |
| `GET` | `/suites/{suiteId}` | Get suite with cases | 200 |
| `PUT` | `/suites/{suiteId}` | Update suite name | 200 |
| `DELETE` | `/suites/{suiteId}` | Delete suite + cases | 204 |

### Cases

| Method | Path | Description | Status |
|--------|------|-------------|--------|
| `GET` | `/suites/{suiteId}/cases` | List cases in suite | 200 |
| `POST` | `/suites/{suiteId}/cases` | Create a case | 201 |
| `PUT` | `/suites/{suiteId}/cases/{caseId}` | Update a case | 200 |
| `DELETE` | `/suites/{suiteId}/cases/{caseId}` | Delete a case | 204 |

### Runs

| Method | Path | Description | Status |
|--------|------|-------------|--------|
| `GET` | `/runs` | List runs (filter by status, suiteId) | 200 |
| `POST` | `/runs` | Create and execute a run | 201 |
| `GET` | `/runs/{runId}` | Get run with results + summary | 200 |
| `DELETE` | `/runs/{runId}` | Delete run + results | 204 |

### Run Creation — Request Body

```json
{
  "suiteId": "string (required)",
  "modelId": "string (required)",
  "baselinePrompt": "string (required, max 10,000 chars)",
  "candidatePrompt": "string (required, max 10,000 chars)",
  "rubric": "string (required)",
  "temperature": 0.7,
  "maxTokens": 1024,
  "caseIds": ["case-id-1", "case-id-2"]
}
```

**Constraints:**
- `baselinePrompt` / `candidatePrompt`: max 10,000 characters
- `temperature`: 0.0 – 1.0
- `maxTokens`: 1 – 4,096
- `caseIds`: max 3 items (omit to auto-select first 3)
- Invocations per case: 4 (2 model calls + 2 evaluations)

### Run Creation — Response (201)

```json
{
  "runId": "...",
  "suiteId": "...",
  "status": "RUNNING",
  "invocations": 12,
  "...": "..."
}
```

### Error Responses

| Status | When |
|--------|------|
| 400 | Missing required fields, validation failure, invalid JSON |
| 404 | Suite or Run not found |
| 405 | HTTP method not supported on route |

---

## Data Models

### Suite

```python
@dataclass
class Suite:
    suite_id: str          # Auto-generated UUID
    name: str              # User-provided name
    created_at: str        # ISO 8601 timestamp
    updated_at: str        # ISO 8601 timestamp
```

### Case

```python
@dataclass
class Case:
    case_id: str           # Auto-generated UUID
    suite_id: str          # Parent suite ID
    input: str             # Test input prompt
    expected_behavior: str # Optional expected behavior
    tags: list[str]        # Optional tags for filtering
    created_at: str
    updated_at: str
```

### Run

```python
@dataclass
class Run:
    run_id: str            # Auto-generated UUID
    suite_id: str          # Reference to suite
    model_id: str          # Bedrock model ID
    baseline_prompt: str   # Baseline prompt text
    candidate_prompt: str  # Candidate prompt text
    rubric: str            # Evaluation rubric
    temperature: float     # 0.0 – 1.0
    max_tokens: int        # 1 – 4096
    status: str            # RUNNING | COMPLETED | PARTIAL | FAILED
    created_at: str
    completed_at: str | None
```

### RunCaseResult

```python
@dataclass
class RunCaseResult:
    run_id: str
    case_id: str
    baseline_output: str | None
    candidate_output: str | None
    baseline_score: int | None      # 1–5
    candidate_score: int | None     # 1–5
    baseline_rationale: str | None
    candidate_rationale: str | None
    baseline_latency_ms: float | None
    candidate_latency_ms: float | None
    classification: str             # Improved | Regressed | Unchanged | Needs review | Failed
    error: str | None
    tags: list[str] | None
    truncated: bool                 # True if output hit max token limit
```

### Classification Logic

```
candidate_score > baseline_score  →  "Improved"
candidate_score < baseline_score  →  "Regressed"
candidate_score == baseline_score →  "Unchanged"
evaluator confidence == "low"     →  "Needs review"
exception during execution        →  "Failed"
```

---

## Bedrock Integration

All Bedrock calls are server-side only (ADR-0004). The Lambda function uses its IAM execution role to invoke models.

### Model Invocation

```
invoke_model(model_id, prompt, temperature, max_tokens)
  → (output_text, latency_ms)
```

- Supports Claude (completion field) and other models (generation field)
- Output truncated with `... [truncated]` if it reaches `max_tokens_to_sample`
- `detect_truncation()` heuristic: output length ≥ max_tokens AND doesn't end with a stop character

### Evaluation

```
evaluate_output(output, rubric, model_id)
  → { score, confidence, rationale, violations }
```

- Same model used for evaluation (or a cheaper allowlisted model)
- Strict JSON response schema enforced by prompt engineering
- Score clamped to 1–5; malformed responses default to `{ score: 3, confidence: "low" }`
- Confidence: high / medium / low (low triggers "Needs review")

### Invocation Count

Each case requires **4 Bedrock invocations**:
1. Baseline model invocation
2. Candidate model invocation
3. Baseline output evaluation
4. Candidate output evaluation

For a 3-case run: **12 invocations total** (returned in the 201 response as `invocations`).

---

## Frontend Architecture

React + TypeScript + Vite, deployed to AWS Amplify.

### Structure

```
frontend/src/
├── api/
│   ├── client.ts          # Typed fetch wrapper (13 functions, ApiError class)
│   └── types.ts           # TypeScript interfaces matching backend models
├── components/
│   ├── ClassificationBadge.tsx  # Color-coded classification pill
│   ├── ErrorBanner.tsx          # Dismiss-able error banner with retry
│   └── SummaryCards.tsx         # 6-card classification summary grid
├── screens/
│   ├── HomeScreen.tsx           # Suite list, create suite
│   ├── SuiteEditorScreen.tsx    # Edit suite, add/edit/delete cases
│   ├── RunConfigScreen.tsx      # Configure and launch a run
│   └── ResultsScreen.tsx        # Results with filters, side-by-side comparison
├── App.tsx                 # Router setup
├── main.tsx                # Entry point
└── styles.css              # Global styles (CSS custom properties)
```

### Routing

| Path | Screen | Description |
|------|--------|-------------|
| `/` | HomeScreen | List suites, create new suite |
| `/suites/:suiteId/edit` | SuiteEditorScreen | Edit suite name, manage cases |
| `/suites/:suiteId/run` | RunConfigScreen | Configure prompts, model, cases |
| `/runs/:runId` | ResultsScreen | View results with filters |

### API Client

- All requests go through `client.ts` functions
- `ApiError` class surfaces HTTP status + message to screens
- Every screen wraps API calls in try/catch with `ErrorBanner`
- `VITE_API_BASE_URL` set at build time (no runtime config)

### Validation (Client-Side)

- Prompt length: max 10,000 characters (shown with character counter)
- Temperature: 0.0 – 1.0 (slider)
- Max tokens: 1 – 4,096 (number input)
- Case selection: max 3 per run

---

## Security Model

| Layer | Mechanism | Notes |
|-------|-----------|-------|
| **Auth** | None (MVP) | Post-MVP scope; no Cognito |
| **CORS** | `AmplifyDomain` parameter | Defaults to `*` for dev; set to Amplify URL on deploy |
| **Bedrock** | Server-side proxy only | No model credentials exposed to frontend |
| **Logging** | Structured metadata only | No raw prompts/outputs in CloudWatch |
| **Validation** | Server + client | Prompt length, temperature, maxTokens, case count |
| **IAM** | Least-privilege | Lambda role: DynamoDB CRUD + Bedrock InvokeModel + CloudWatch Logs |
| **DynamoDB** | Single-table, no public access | Only Lambda role can read/write |

### What's NOT in MVP

- Authentication / authorization
- Rate limiting (beyond API Gateway defaults)
- VPC / private subnets
- WAF
- Encryption at rest (DynamoDB default encryption)
- Prompt content scanning

---

## Cost Profile

All resources use pay-per-request pricing. Estimated monthly cost for light usage (< 50 runs):

| Service | Config | Est. Monthly |
|---------|--------|-------------|
| DynamoDB | PAY_PER_REQUEST, single table | < $1 |
| Lambda | 256MB, ~5s avg, < 500 invocations | < $1 |
| API Gateway | REST API, < 1,000 requests | < $1 |
| Bedrock | 4 invocations per case, ~12 per run | Variable (model-dependent) |
| Amplify | Hosting, < 5GB served | < $1 |
| CloudWatch | Logs, minimal | < $1 |
| **Total** | | **< $5/month** (excluding Bedrock) |

Bedrock costs depend on the model selected and tokens consumed. Claude 3 Haiku is the most cost-effective option for the demo.

---

## Key Design Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| ADR-001 | DynamoDB design | Single table, PK/SK pattern | Low operational complexity for MVP; supports all access patterns |
| ADR-002 | Run execution | Synchronous Lambda | Clearest live demo; keeps code small; 3 cases × 4 calls = ~30s |
| ADR-003 | Evaluation | Bedrock rubric scoring | Consistent with prompt execution; strict JSON schema for reliability |
| ADR-004 | Bedrock access | Server-side proxy | No frontend credentials; Lambda IAM role handles auth |

Full ADRs in `docs/adr/0001-0004`.

---

## Repository Structure

```
prompt-lens/
├── backend/
│   ├── src/handlers/api/
│   │   ├── __init__.py          # Lambda handler entry point
│   │   ├── handler.py           # Route dispatch
│   │   ├── bedrock.py           # Bedrock invoke + evaluate
│   │   ├── dynamodb.py          # DynamoDB operations
│   │   ├── seed.py              # Demo data seeder
│   │   ├── models/              # Dataclasses (Suite, Case, Run, RunCaseResult)
│   │   └── routes/              # Route handlers (suites, cases, runs)
│   ├── tests/                   # 202 pytest tests (moto-mocked)
│   ├── template.yaml            # SAM template
│   ├── samconfig.toml           # SAM deploy config
│   └── requirements.txt         # boto3, moto, pytest
├── frontend/
│   ├── src/                     # React app (6 tests)
│   ├── .env.example             # VITE_API_BASE_URL template
│   └── package.json
├── docs/
│   ├── adr/0001-0004            # Architecture Decision Records
│   ├── architecture.md          # This file
│   └── superpowers/             # Implementation plans (historical)
├── .scratch/wayfinder/          # Feature breakdown + tickets
├── CONTEXT.md                   # Domain model glossary
├── README.md                    # Project overview + deploy steps
└── sam                          # SAM CLI wrapper (runs in backend/)
```
