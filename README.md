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

## Frontend

The React frontend lives in `frontend/`. See `frontend/README.md` for setup. The API base URL is configured via `VITE_API_BASE_URL` (see `.env.example`).
