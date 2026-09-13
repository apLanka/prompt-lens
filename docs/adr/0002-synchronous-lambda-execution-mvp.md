# 0002: Synchronous Lambda Execution for MVP

We decided to run the Lambda function synchronously for the MVP, processing up to 3 cases in a single invocation. This creates the clearest live demo and keeps the code small.

For each case, the Lambda:
1. Validates limits and resolves the model alias
2. Builds generation requests for baseline and candidate prompts
3. Calls Bedrock for both outputs
4. Calls Bedrock evaluator with strict JSON instructions
5. Validates evaluator JSON, calculates status, writes run-case record
6. Returns collected results

We chose synchronous over asynchronous (SQS + worker Lambda) because:
1. The MVP caps runs at 20 cases, with a target of 3-case demos under 60 seconds
2. Synchronous is simpler to implement and debug
3. Provides immediate feedback to the user

For production with larger runs, we'll evolve to asynchronous execution with SQS to avoid API Gateway timeout pressure and improve resilience.
