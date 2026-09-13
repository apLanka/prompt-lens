# Infrastructure Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up the foundational AWS infrastructure including DynamoDB table, IAM execution role, API Gateway, and Lambda function skeleton with SAM deployment configuration.

**Architecture:** Single-table DynamoDB design with PK/SK pattern, Lambda function as API handler with least-privilege IAM permissions, API Gateway HTTP API for public interface, all defined as Infrastructure as Code using AWS SAM.

**Tech Stack:** AWS SAM (Serverless Application Model), Python 3.11 Lambda runtime, DynamoDB, API Gateway HTTP API, IAM

**Spec:** [Feature 1 Ticket](../../.scratch/wayfinder/tickets/01-infrastructure-scaffold.md)

## Global Constraints

- DynamoDB table name: `PromptLens`
- Partition key: `PK` (String)
- Sort key: `SK` (String)
- Lambda runtime: Python 3.11
- SAM template required for deployment
- No hardcoded credentials; use IAM execution roles
- CORS enabled for frontend integration
- All resources must be tagged for cost tracking

---

## File Structure

```
prompt-lens/
├── template.yaml                    # SAM template (main IaC file)
├── samconfig.toml                   # SAM CLI configuration
├── README.md                        # Deployment instructions (created here, expanded in ticket 07)
└── src/
    └── handlers/
        └── api/
            └── __init__.py          # Lambda handler placeholder
```

---

## Task 1: Initialize SAM Project

**Files:**
- Create: `template.yaml`
- Create: `samconfig.toml`

**Interfaces:**
- Consumes: None (initial setup)
- Produces: SAM template with basic structure

- [ ] **Step 1: Create SAM template with basic structure**

Create `template.yaml` with the following content:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: PromptLens - Prompt Regression Testing Tool

Globals:
  Function:
    Timeout: 30
    Runtime: python3.11
    MemorySize: 256
    Tracing: Active
    Environment:
      Variables:
        TABLE_NAME: !Ref PromptLensTable

Resources:
  # Resources will be added in subsequent tasks

Outputs:
  ApiEndpoint:
    Description: API Gateway endpoint URL
    Value: !Sub "https://${ServerlessRestApi}.execute-api.${AWS::Region}.amazonaws.com/Prod/"
```

- [ ] **Step 2: Create SAM configuration**

Create `samconfig.toml` with the following content:

```toml
version = 0.1

[default]
[default.deploy]
[default.deploy.parameters]
stack_name = "promptlens"
resolve_s3 = true
s3_prefix = "promptlens"
region = "us-east-1"
confirm_changeset = true
capabilities = "CAPABILITY_IAM"
disable_rollback = false
parameter_overrides = ""
image_repositories = []
```

- [ ] **Step 3: Validate SAM template**

Run: `sam validate`
Expected: Template is valid

- [ ] **Step 4: Commit**

```bash
git add template.yaml samconfig.toml
git commit -m "chore: initialize SAM project structure"
```

---

## Task 2: Create DynamoDB Table

**Files:**
- Modify: `template.yaml` (add DynamoDB resource)

**Interfaces:**
- Consumes: None
- Produces: DynamoDB table resource for use by Lambda

- [ ] **Step 1: Add DynamoDB table to template.yaml**

Add the following resource under `Resources:` section:

```yaml
  PromptLensTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: PromptLens
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: PK
          AttributeType: S
        - AttributeName: SK
          AttributeType: S
      KeySchema:
        - AttributeName: PK
          KeyType: HASH
        - AttributeName: SK
          KeyType: RANGE
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: false
      Tags:
        - Key: Project
          Value: PromptLens
        - Key: Environment
          Value: Dev
```

- [ ] **Step 2: Validate SAM template**

Run: `sam validate`
Expected: Template is valid

- [ ] **Step 3: Deploy to verify table creation**

Run: `sam deploy --guided --no-confirm-changeset`
Expected: Stack deploys successfully, DynamoDB table created

- [ ] **Step 4: Verify table in AWS Console or CLI**

Run: `aws dynamodb describe-table --table-name PromptLens`
Expected: Table exists with PK and SK attributes

- [ ] **Step 5: Clean up test deployment**

Run: `sam delete --stack-name promptlens --no-prompts`
Expected: Stack deleted

- [ ] **Step 6: Commit**

```bash
git add template.yaml
git commit -m "feat: add DynamoDB table with single-table design"
```

---

## Task 3: Create IAM Execution Role

**Files:**
- Modify: `template.yaml` (add IAM role and policies)

**Interfaces:**
- Consumes: PromptLensTable resource
- Produces: IAM role for Lambda execution with DynamoDB, Bedrock, and CloudWatch permissions

- [ ] **Step 1: Add IAM role to template.yaml**

Add the following resource under `Resources:` section:

```yaml
  LambdaExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: PromptLensLambdaRole
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: PromptLensDynamoDBPolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - dynamodb:GetItem
                  - dynamodb:PutItem
                  - dynamodb:UpdateItem
                  - dynamodb:DeleteItem
                  - dynamodb:Query
                  - dynamodb:Scan
                Resource:
                  - !GetAtt PromptLensTable.Arn
                  - !Sub "${PromptLensTable.Arn}/index/*"
        - PolicyName: PromptLensBedrockPolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - bedrock:InvokeModel
                Resource: "*"
        - PolicyName: PromptLensCloudWatchPolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - logs:CreateLogGroup
                  - logs:CreateLogStream
                  - logs:PutLogEvents
                Resource: "*"
```

- [ ] **Step 2: Validate SAM template**

Run: `sam validate`
Expected: Template is valid

- [ ] **Step 3: Deploy to verify IAM role creation**

Run: `sam deploy --guided --no-confirm-changeset`
Expected: Stack deploys successfully, IAM role created

- [ ] **Step 4: Verify IAM role in AWS Console or CLI**

Run: `aws iam get-role --role-name PromptLensLambdaRole`
Expected: Role exists with correct trust policy

- [ ] **Step 5: Clean up test deployment**

Run: `sam delete --stack-name promptlens --no-prompts`
Expected: Stack deleted

- [ ] **Step 6: Commit**

```bash
git add template.yaml
git commit -m "feat: add IAM execution role with least-privilege permissions"
```

---

## Task 4: Create Lambda Function Skeleton

**Files:**
- Modify: `template.yaml` (add Lambda function)
- Create: `src/handlers/api/__init__.py`

**Interfaces:**
- Consumes: PromptLensTable, LambdaExecutionRole
- Produces: Lambda function with handler structure for API implementation

- [ ] **Step 1: Add Lambda function to template.yaml**

Add the following resource under `Resources:` section:

```yaml
  ApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: PromptLensApi
      Handler: src.handlers.api.handler
      CodeUri: .
      Description: PromptLens API Handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Events:
        CatchAll:
          Type: Api
          Properties:
            Path: /{proxy+}
            Method: ANY
            RestApiId: !Ref ServerlessRestApi
        Root:
          Type: Api
          Properties:
            Path: /
            Method: ANY
            RestApiId: !Ref ServerlessRestApi
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref PromptLensTable
        - BedrockInvokeModelPolicy:
            ModelId: "*"
```

- [ ] **Step 2: Create Lambda handler placeholder**

Create `src/handlers/api/__init__.py` with the following content:

```python
"""PromptLens API Lambda Handler."""

import json
import os
from typing import Any, Dict


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for API requests.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    table_name = os.environ.get("TABLE_NAME", "PromptLens")
    
    # Health check endpoint
    if event.get("path") == "/health":
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({
                "status": "healthy",
                "table": table_name,
            }),
        }
    
    # Default response for unimplemented routes
    return {
        "statusCode": 404,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({
            "message": "Not found",
        }),
    }
```

- [ ] **Step 3: Add API Gateway to template.yaml**

Add the following resource under `Resources:` section (before Lambda function):

```yaml
  ServerlessRestApi:
    Type: AWS::Serverless::Api
    Properties:
      StageName: Prod
      Cors:
        AllowMethods: "'GET,POST,PUT,PATCH,DELETE,OPTIONS'"
        AllowHeaders: "'Content-Type,Authorization'"
        AllowOrigin: "'*'"
      TracingEnabled: true
```

- [ ] **Step 4: Validate SAM template**

Run: `sam validate`
Expected: Template is valid

- [ ] **Step 5: Build and deploy to verify Lambda function**

Run: `sam build && sam deploy --guided --no-confirm-changeset`
Expected: Stack deploys successfully, Lambda function created

- [ ] **Step 6: Test health check endpoint**

Run: `curl https://<api-id>.execute-api.us-east-1.amazonaws.com/Prod/health`
Expected: `{"status": "healthy", "table": "PromptLens"}`

- [ ] **Step 7: Clean up test deployment**

Run: `sam delete --stack-name promptlens --no-prompts`
Expected: Stack deleted

- [ ] **Step 8: Commit**

```bash
git add template.yaml src/handlers/api/__init__.py
git commit -m "feat: add Lambda function skeleton with health check endpoint"
```

---

## Task 5: Add Outputs and Finalize Template

**Files:**
- Modify: `template.yaml` (add outputs)

**Interfaces:**
- Consumes: All resources
- Produces: CloudFormation outputs for API endpoint, table name, function name

- [ ] **Step 1: Add outputs to template.yaml**

Replace the existing `Outputs:` section with:

```yaml
Outputs:
  ApiEndpoint:
    Description: API Gateway endpoint URL
    Value: !Sub "https://${ServerlessRestApi}.execute-api.${AWS::Region}.amazonaws.com/Prod/"
    Export:
      Name: PromptLensApiEndpoint
  
  DynamoDBTableName:
    Description: DynamoDB table name
    Value: !Ref PromptLensTable
    Export:
      Name: PromptLensTableName
  
  LambdaFunctionName:
    Description: Lambda function name
    Value: !Ref ApiFunction
    Export:
      Name: PromptLensFunctionName
  
  IAMRoleArn:
    Description: IAM execution role ARN
    Value: !GetAtt LambdaExecutionRole.Arn
    Export:
      Name: PromptLensRoleArn
```

- [ ] **Step 2: Validate SAM template**

Run: `sam validate`
Expected: Template is valid

- [ ] **Step 3: Final deployment test**

Run: `sam build && sam deploy --guided --no-confirm-changeset`
Expected: Stack deploys successfully with all outputs

- [ ] **Step 4: Verify all outputs**

Run: `aws cloudformation describe-stacks --stack-name promptlens --query "Stacks[0].Outputs"`
Expected: All 4 outputs present

- [ ] **Step 5: Clean up test deployment**

Run: `sam delete --stack-name promptlens --no-prompts`
Expected: Stack deleted

- [ ] **Step 6: Commit**

```bash
git add template.yaml
git commit -m "feat: add CloudFormation outputs for all resources"
```

---

## Task 6: Create README with Deployment Instructions

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: All previous tasks
- Produces: Documentation for deployment and usage

- [ ] **Step 1: Create README.md**

Create `README.md` with the following content:

```markdown
# PromptLens

A lightweight prompt-regression testing workspace for AI engineers. Compares two prompt versions against saved test cases, invokes Amazon Bedrock models, scores results against rubrics, and highlights regressions.

## Prerequisites

- AWS CLI configured with appropriate credentials
- AWS SAM CLI installed
- Python 3.11+
- Node.js 18+ (for frontend, future tasks)

## Deployment

### 1. Build the application

```bash
sam build
```

### 2. Deploy to AWS

```bash
sam deploy --guided
```

Follow the prompts:
- Stack Name: `promptlens`
- AWS Region: `us-east-1` (or your preferred region)
- Confirm changes before deploy: `Y`
- Allow SAM CLI IAM role creation: `Y`
- Disable rollback: `N`
- PromptLensApi Function has no authentication: `Y`

### 3. Verify deployment

```bash
# Get API endpoint
aws cloudformation describe-stacks --stack-name promptlens --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text

# Test health check
curl <api-endpoint>/health
```

## Cleanup

```bash
sam delete --stack-name promptlens
```

## Architecture

- **DynamoDB**: Single-table design with PK/SK pattern
- **Lambda**: Python 3.11 runtime with least-privilege IAM
- **API Gateway**: HTTP API with CORS enabled
- **Bedrock**: For prompt execution and evaluation (configured in subsequent tasks)

## Cost Considerations

- DynamoDB: PAY_PER_REQUEST (no idle costs)
- Lambda: Pay per invocation
- API Gateway: Pay per request
- Estimated cost for development/testing: < $5/month

## Security

- No hardcoded credentials
- IAM execution role with least-privilege permissions
- CORS configured for frontend integration
- All data encrypted at rest and in transit
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add deployment instructions and architecture overview"
```

---

## Verification Checklist

After completing all tasks, verify:

- [ ] SAM template validates successfully
- [ ] DynamoDB table created with PK/SK attributes
- [ ] IAM role created with DynamoDB, Bedrock, and CloudWatch permissions
- [ ] Lambda function deployed and responding to health check
- [ ] API Gateway with CORS enabled
- [ ] All resources tagged for cost tracking
- [ ] README documents deployment process
- [ ] No hardcoded credentials in any files
- [ ] Stack can be deployed and deleted cleanly

## Next Steps

After completing this infrastructure scaffold:

1. **Task 02: Suite Management** - Implement CRUD operations for Suites and Cases
2. Configure Bedrock model access in AWS console
3. Set up Amplify hosting for frontend (Task 07)

## Troubleshooting

### Common Issues

1. **SAM build fails**: Ensure Python 3.11+ is installed and in PATH
2. **Deployment fails**: Check AWS credentials and permissions
3. **Lambda timeout**: Increase timeout in template.yaml if needed
4. **CORS errors**: Verify API Gateway CORS configuration

### Debug Commands

```bash
# Check SAM template
sam validate --lint

# View stack events
aws cloudformation describe-stack-events --stack-name promptlens

# Check Lambda logs
sam logs -n PromptLensApi --stack-name promptlens --tail
```
