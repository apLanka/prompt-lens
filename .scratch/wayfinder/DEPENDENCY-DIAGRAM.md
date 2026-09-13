# PromptLens MVP - Dependency Diagram

## Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    WEEKEND BUILD TIMELINE                       │
├─────────────────────────────────────────────────────────────────┤
│  FRIDAY EVENING          SATURDAY              SUNDAY          │
│  ─────────────          ────────              ──────          │
│  Scaffold               Integrate             Deploy           │
│  Foundation             Bedrock               Polish           │
└─────────────────────────────────────────────────────────────────┘

## Feature Dependencies

```
                              ┌──────────────────────┐
                              │  01 Infrastructure   │
                              │     Scaffold         │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  02 Suite Management │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  03 Run Execution    │
                              └──────────┬───────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
         ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
         │ 04 Results &     │  │ 06 Safety &      │  │                  │
         │    Review        │  │    Guardrails    │  │                  │
         └────────┬─────────┘  └────────┬─────────┘  │                  │
                  │                     │            │                  │
                  └──────────┬──────────┘            │                  │
                             │                       │                  │
                             ▼                       │                  │
                  ┌──────────────────┐               │                  │
                  │ 05 Frontend UI   │               │                  │
                  └────────┬─────────┘               │                  │
                           │                         │                  │
                           └──────────┬──────────────┘                  │
                                      │                                 │
                                      ▼                                 │
                           ┌──────────────────┐                         │
                           │ 07 Deployment &  │                         │
                           │    Polish        │                         │
                           └──────────────────┘                         │
                                                                        │
```

## Parallelization Map

```
Sequential Path (Critical Path):
01 → 02 → 03 → 04 → 05 → 07

Parallel Opportunities:
- 06 can run parallel to 04 (both depend on 03)
- 05 can start early with API contracts
- Documentation can be written throughout

Estimated Time Savings:
- With parallelization: ~2.5 days
- Without parallelization: ~3 days
```

## Milestone Checkpoints

```
┌─────────────────────────────────────────────────────────────────┐
│ MILESTONE 1: Infrastructure Ready                               │
│ ─────────────────────────────────                              │
│ ✓ DynamoDB table created                                        │
│ ✓ IAM role configured                                          │
│ ✓ API Gateway deployed                                         │
│ ✓ Lambda function responding                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ MILESTONE 2: Core Backend Functional                           │
│ ─────────────────────────────────────                          │
│ ✓ Suite CRUD operations working                                │
│ ✓ Run execution with Bedrock                                   │
│ ✓ Results storage and retrieval                                │
│ ✓ Evaluator scoring 1-5                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ MILESTONE 3: UI Complete                                        │
│ ─────────────────────────────                                  │
│ ✓ All screens implemented                                      │
│ ✓ API integration working                                      │
│ ✓ Results display functional                                   │
│ ✓ Error handling comprehensive                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ MILESTONE 4: Production Ready                                   │
│ ─────────────────────────────                                  │
│ ✓ Deployed to Amplify                                          │
│ ✓ Safety guardrails active                                     │
│ ✓ Documentation complete                                       │
│ ✓ Demo screenshots captured                                    │
│ ✓ 3-case run completes in <60 seconds                          │
└─────────────────────────────────────────────────────────────────┘
```

## Risk Areas

1. **Bedrock Model Access**: Ensure model access is enabled in target region before starting ticket 03
2. **Lambda Timeout**: Synchronous execution may hit Lambda timeout for 3 cases; may need to optimize
3. **DynamoDB Limits**: Ensure items stay under 400KB; truncate oversized output
4. **CORS Configuration**: Must be configured correctly for Amplify domain

## Success Criteria

- [ ] Public Amplify URL loads successfully
- [ ] Seeded demo suite contains at least 3 cases
- [ ] Baseline and candidate prompts run against same cases
- [ ] Each completed case has 2 outputs, 2 scores, rationale, and status
- [ ] Results viewable after browser refresh
- [ ] 3-case demo completes reliably in under 60 seconds
- [ ] App uses Amplify, API Gateway, Lambda, DynamoDB, and Bedrock
- [ ] Repository includes deployment instructions and documentation
