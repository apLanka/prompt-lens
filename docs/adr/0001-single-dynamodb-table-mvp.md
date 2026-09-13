# 0001: Single DynamoDB Table for MVP

We decided to use a single DynamoDB table with partition key (PK) and sort key (SK) pattern for the MVP, storing Suites, Cases, Runs, and Run-Case Results in one table. This keeps deployment small and operational complexity low while supporting all required access patterns through key design.

The single-table design uses prefixed keys:
- `SUITE#{suiteId}` as PK for Suites and their Cases
- `RUN#{runId}` as PK for Runs and their Run-Case Results

We chose this over a multi-table approach because:
1. The MVP has simple access patterns that fit single-table design
2. One table means one IAM permission scope for Lambda
3. Reduces deployment and operational overhead for a weekend build

Post-MVP, if query patterns become complex or access patterns diverge significantly, we can migrate to multi-table without changing the API surface.
