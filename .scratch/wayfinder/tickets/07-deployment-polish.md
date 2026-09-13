# 07: Deployment & Polish

**What to build:** Deploy the frontend to AWS Amplify, configure CORS, polish the results page, add comprehensive error handling, and capture architecture and demo screenshots for documentation.

**Blocked by:** 05-frontend-ui, 06-safety-guardrails

**Status:** ready-for-agent

## Scope & Boundary

**Owns:**
- AWS Amplify hosting configuration
- CORS restriction to Amplify domain
- Results page UI polish
- Comprehensive error handling across all screens
- Architecture diagram capture
- Demo screenshots for Builder Center article
- Deployment documentation
- Environment variable documentation

**Delegates:**
- Backend infrastructure (handled in ticket 01)
- Application logic (handled in tickets 02-06)
- Cognito authentication (post-MVP)

## Core Entities / Data Models

**Deployment Configuration:**
- Amplify app connected to GitHub repository
- API base URL environment variable set
- CORS headers configured for Amplify domain

**Documentation:**
- Deployment instructions
- Environment variable notes
- Cost/safety guidance
- Architecture diagram
- Demo screenshots

## Technical Dependencies & Pre-requisites

- 05-frontend-ui completed
- 06-safety-guardrails completed
- GitHub repository created and connected to Amplify
- Amplify CLI configured

## Acceptance Criteria

- [ ] Public Amplify URL loads successfully
- [ ] App functions identically to local development
- [ ] API CORS restricted to Amplify domain only
- [ ] Results page polished with clear visual hierarchy
- [ ] Error handling covers all API failure scenarios
- [ ] User-friendly error messages displayed for all failures
- [ ] Technical errors logged to CloudWatch with correlation IDs
- [ ] Architecture diagram captured and documented
- [ ] Demo screenshots captured for 3-case run
- [ ] README includes deployment instructions
- [ ] README includes environment variable documentation
- [ ] README includes cost/safety guidance
- [ ] Seeded demo suite works end-to-end on production
