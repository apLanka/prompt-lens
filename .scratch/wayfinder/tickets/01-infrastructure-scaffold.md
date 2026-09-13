# 01: Infrastructure Scaffold

**What to build:** Set up the foundational AWS infrastructure including DynamoDB table, IAM execution role, API Gateway, and Lambda function skeleton. Create the deployment configuration using AWS SAM or CDK.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

## Scope & Boundary

**Owns:**
- DynamoDB table creation with single-table design (PK/SK)
- IAM execution role with least-privilege permissions
- API Gateway HTTP API configuration
- Lambda function skeleton with handler structure
- SAM/CDK deployment templates

**Delegates:**
- Bedrock model access configuration (done in AWS console)
- Amplify hosting setup (done separately in ticket 07)
- Application logic implementation (done in subsequent tickets)

## Core Entities / Data Models

- **DynamoDB Table**: `PromptLens` table with `PK` (partition key) and `SK` (sort key)
- **IAM Role**: Lambda execution role with DynamoDB, Bedrock, and CloudWatch permissions

## Technical Dependencies & Pre-requisites

- AWS CLI configured with appropriate credentials
- SAM CLI or CDK installed
- Bedrock model access enabled in target AWS region

## Acceptance Criteria

- [ ] DynamoDB table `PromptLens` created with PK and SK attributes
- [ ] IAM execution role created with permissions for DynamoDB, Bedrock, and CloudWatch
- [ ] API Gateway HTTP API deployed with CORS configured
- [ ] Lambda function deployed and responding to health check endpoint
- [ ] SAM/CDK template can deploy entire stack with single command
- [ ] No hardcoded credentials in any configuration files
