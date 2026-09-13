# 06: Safety & Guardrails

**What to build:** Implement validation and limits to control cost and prevent abuse. Include max cases limit, input/prompt length limits, output token limits, and CloudWatch logging with structured metadata.

**Blocked by:** 03-run-execution

**Status:** ready-for-agent

## Scope & Boundary

**Owns:**
- API Gateway request validation
- Lambda-side input validation
- Maximum cases limit (20 for MVP)
- Prompt and input length limits
- Output token limits
- CloudWatch structured logging (IDs, sizes, durations, status, errors)
- Estimated invocation count display

**Delegates:**
- Bedrock model access controls (server-side only)
- Authentication and authorization (post-MVP)
- Cost dashboards and alerts (post-MVP)

## Core Entities / Data Models

**Validation Rules:**
- Max cases per run: 20
- Max prompt length: TBD (based on Bedrock model limits)
- Max input length: TBD (based on Bedrock model limits)
- Max output tokens: Configurable per run

**CloudWatch Log Structure:**
- runId, caseId
- inputSize, outputSize
- duration
- status (COMPLETED, PARTIAL, FAILED)
- error (if applicable)

## Technical Dependencies & Pre-requisites

- 03-run-execution completed
- Lambda function with CloudWatch Logs permissions
- API Gateway request validation configuration

## Acceptance Criteria

- [ ] API Gateway validates request payload size and structure
- [ ] Lambda validates case count ≤ 20
- [ ] Lambda validates prompt and input length limits
- [ ] Lambda validates output token configuration
- [ ] Estimated invocation count shown before run starts
- [ ] CloudWatch logs include runId, caseId, sizes, duration, status, errors
- [ ] No full prompts or outputs logged in production (IDs only)
- [ ] Validation errors return clear, user-friendly messages
- [ ] Oversized model output truncated with explicit indicator
- [ ] DynamoDB items stay under 400KB limit
