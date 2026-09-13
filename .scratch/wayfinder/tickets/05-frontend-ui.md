# 05: Frontend UI

**What to build:** Implement the React + TypeScript + Vite frontend with key screens: Home (suite list), Suite Editor (cases + prompt editor), Run Configuration, and Results display. Deploy through AWS Amplify.

**Blocked by:** 02-suite-management, 04-results-review

**Status:** ready-for-agent

## Scope & Boundary

**Owns:**
- React application structure and routing
- Home screen (suite list, demo access)
- Suite Editor screen (case list + baseline/candidate prompt editor)
- Run Configuration screen (model, temperature, tokens, rubric, case selection)
- Results screen (summary cards, filters, side-by-side comparison)
- API client for backend communication
- Build-time environment variable for API base URL

**Delegates:**
- Backend API implementation (handled in tickets 02, 03, 04)
- Amplify hosting configuration (handled in ticket 07)
- Bedrock model configuration (server-side only)

## Core Entities / Data Models

**Frontend State:**
- Suites list
- Current suite with cases
- Run configuration (prompts, model, settings, rubric)
- Run results

**API Contract:**
- GET /suites → Suite[]
- POST /suites → Suite
- GET /suites/{suiteId} → Suite with Cases
- PATCH /suites/{suiteId} → Suite
- DELETE /suites/{suiteId} → void
- POST /suites/{suiteId}/cases → Case
- PATCH /suites/{suiteId}/cases/{caseId} → Case
- DELETE /suites/{suiteId}/cases/{caseId} → void
- POST /runs → Run
- GET /runs/{runId} → Run with Results

## Technical Dependencies & Pre-requisites

- 02-suite-management completed (for suite/case API endpoints)
- 04-results-review completed (for results API endpoint)
- Node.js and npm/yarn installed
- Amplify CLI configured

## Acceptance Criteria

- [ ] React app builds and runs locally with Vite
- [ ] Home screen lists all suites and opens seeded demo
- [ ] Suite Editor displays case list and baseline/candidate prompt editors
- [ ] Run Configuration screen allows model selection, temperature, tokens, rubric, case selection
- [ ] Results screen shows summary cards and status filters
- [ ] Results screen shows side-by-side case comparison
- [ ] All screens responsive and functional on desktop
- [ ] API base URL read from VITE_API_BASE_URL environment variable
- [ ] No AWS credentials or Bedrock configuration in frontend code
- [ ] App handles API errors gracefully with user-friendly messages
- [ ] Initial UI load under 3 seconds on typical broadband
