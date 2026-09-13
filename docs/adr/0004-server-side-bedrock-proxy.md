# 0004: Server-Side Bedrock Proxy (No Client-Side Credentials)

We decided to proxy all Bedrock calls through the Lambda function, keeping all AWS credentials and model configuration server-side. The frontend stores no AWS secrets, Bedrock credentials, or unrestricted model configuration.

The frontend reads only the API base URL from a build-time environment variable (VITE_API_BASE_URL). All Bedrock invocations happen in Lambda with IAM execution role permissions.

We chose this because:
1. Security: No credentials exposed to the browser; reduces attack surface
2. Control: Server-side validation enforces allowed models, token limits, and rate limits
3. Cost protection: Can implement spending guards before public launch

The trade-off is added latency (client → API Gateway → Lambda → Bedrock → Lambda → API Gateway → client), but this is acceptable for the MVP's synchronous execution model.

For production, we'll add Cognito authentication before public launch to prevent unbounded public Bedrock spending.
