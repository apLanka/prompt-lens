# PromptLens MVP - Wayfinder Map

## Destination

A working prompt-regression testing tool deployed on AWS that allows users to create test suites, run baseline vs candidate prompt comparisons against Bedrock models, evaluate results with AI scoring, and view side-by-side analysis. The MVP should be demonstrable end-to-end in under 60 seconds for a 3-case run.

## Notes

- **Tech Stack**: React + TypeScript + Vite (frontend), AWS Lambda + API Gateway + DynamoDB + Bedrock + Amplify (backend)
- **Domain Glossary**: See CONTEXT.md for entity definitions (Suite, Case, Run, Run-Case Result, etc.)
- **Architecture Decisions**: See docs/adr/ for key decisions (single-table DynamoDB, synchronous Lambda, Bedrock evaluation, server-side proxy)
- **Weekend Build Timeline**: Friday (scaffold), Saturday (integrate Bedrock), Sunday (deploy + polish)
- **MVP Constraints**: 20 cases max, text-only, single model selection, no auth, synchronous execution

## Decisions so far

- [0001: Single DynamoDB Table](../../docs/adr/0001-single-dynamodb-table-mvp.md): Using single table with PK/SK pattern for MVP simplicity
- [0002: Synchronous Lambda Execution](../../docs/adr/0002-synchronous-lambda-execution-mvp.md): Synchronous processing for up to 3 cases for clearest demo
- [0003: Bedrock-Based Evaluation](../../docs/adr/0003-bedrock-based-evaluation.md): Using Bedrock with strict JSON schema for evaluation scoring
- [0004: Server-Side Bedrock Proxy](../../docs/adr/0004-server-side-bedrock-proxy.md): All Bedrock calls through Lambda; no client-side credentials

## Not yet specified

- Exact Bedrock model allowlist (cost vs capability trade-offs)
- Detailed error handling UX for partial failures
- Seed data content for demo suite
- Specific UI component library choice (if any beyond basic HTML/CSS)
- CloudWatch dashboard metrics and alarms configuration

## Out of scope

- Authentication and multi-tenancy (post-MVP)
- CI/CD integration and webhooks (V2)
- Multimodal inputs (V2)
- Statistical benchmarking and vector search (V3)
- Real customer data usage (privacy constraint)
