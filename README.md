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
