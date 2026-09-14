# PromptLens Architecture

```
┌──────────────┐      ┌─────────────────────────────────────────────────────────┐
│   Frontend   │─────▶│  API Gateway (REST)                                     │
│   (React +   │      │  CORS: AMPLIFY_DOMAIN param (default: *)                │
│    Vite)     │◀─────│                                                         │
│   Amplify    │      └────────────────────────┬────────────────────────────────┘
└──────────────┘                               │
                                        ┌──────▼──────┐
                                        │   Lambda     │
                                        │   (Python    │
                                        │    3.11)     │
                                        └──────┬──────┘
                                               │
                              ┌────────────────┼────────────────┐
                              │                │                │
                        ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
                        │ DynamoDB  │   │  Bedrock  │   │CloudWatch │
                        │ (single   │   │ (invoke   │   │ (structured│
                        │  table)   │   │  model +  │   │  logging) │
                        │           │   │  evaluate)│   │           │
                        └───────────┘   └───────────┘   └───────────┘
```

## Key Design Decisions

| Decision | Choice | ADR |
|----------|--------|-----|
| DynamoDB design | Single table, PK/SK pattern | `docs/adr/0001-...` |
| Run execution | Synchronous Lambda (max 3 cases, ≤60s) | `docs/adr/0002-...` |
| Evaluation | Bedrock rubric scoring, strict JSON schema | `docs/adr/0003-...` |
| Bedrock access | Server-side proxy only, no frontend keys | `docs/adr/0004-...` |

## Data Flow

1. **Create Run** → API validates input → writes `RUN#` item to DynamoDB
2. **Execute** → for each case: invoke model (×2) → evaluate outputs (×2) → write `RESULT#` items
3. **Read Results** → API reads `RUN#` + queries `RESULT#` items → returns with summary statistics

## Security Model

- **No auth in MVP** — post-MVP scope
- **CORS** — restricted to Amplify domain via `AmplifyDomain` template parameter
- **Bedrock** — invoked server-side only; no model credentials exposed to frontend
- **Logging** — structured metadata (IDs, sizes, durations) only; no raw prompts/outputs
