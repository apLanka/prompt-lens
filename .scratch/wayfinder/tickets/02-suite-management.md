# 02: Suite Management

**What to build:** Implement CRUD operations for test Suites and their Cases. Users can create, view, rename, and delete Suites; add, edit, and delete Cases within Suites. Includes seed data for a demo suite.

**Blocked by:** 01-infrastructure-scaffold

**Status:** ready-for-agent

## Scope & Boundary

**Owns:**
- Suite CRUD operations (create, read, update, delete)
- Case CRUD operations within Suites
- DynamoDB operations for Suite and Case entities
- Seed data population for demo suite
- API endpoints for Suite and Case management

**Delegates:**
- Run execution (handled in ticket 03)
- Frontend UI (handled in ticket 05)
- Authentication (out of scope for MVP)

## Core Entities / Data Models

**Suite:**
- PK = `SUITE#{suiteId}`
- SK = `META`
- Fields: name, createdAt, updatedAt

**Case:**
- PK = `SUITE#{suiteId}`
- SK = `CASE#{caseId}`
- Fields: input, expectedBehavior, tags

## Technical Dependencies & Pre-requisites

- 01-infrastructure-scaffold completed
- DynamoDB table available
- Lambda function with DynamoDB permissions

## Acceptance Criteria

- [ ] POST /suites creates a new suite with generated ID
- [ ] GET /suites lists all suites
- [ ] GET /suites/{suiteId} returns suite with all its cases
- [ ] PATCH /suites/{suiteId} renames a suite
- [ ] DELETE /suites/{suiteId} deletes suite and all its cases
- [ ] POST /suites/{suiteId}/cases adds a new case
- [ ] PATCH /suites/{suiteId}/cases/{caseId} edits a case
- [ ] DELETE /suites/{suiteId}/cases/{caseId} deletes a case
- [ ] Seed data creates demo suite with at least 3 cases
- [ ] All operations validate input and return appropriate error responses
- [ ] Cases cannot exist without a parent Suite
