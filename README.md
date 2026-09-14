# PromptLens

A lightweight prompt-regression testing workspace for AI engineers. Compares two prompt versions against saved test cases, invokes Amazon Bedrock models, scores results against rubrics, and highlights regressions.

## Repository layout

```
prompt-lens/
├── backend/    # Python 3.11 Lambda + SAM (API, DynamoDB, Bedrock)
├── frontend/   # React + TypeScript + Vite
├── docs/       # ADRs, architecture diagram, implementation plans
└── sam         # SAM CLI wrapper (runs in backend/)
```

See `backend/README.md` and `frontend/README.md` for package-specific setup.

## Quickstart

**Backend** — test and deploy:

```bash
cd backend && .venv/bin/python -m pytest tests/ -q   # 202 tests
cd .. && ./sam build && ./sam deploy --guided       # deploy (stack: promptlens)
```

**Frontend** — run locally:

```bash
cd frontend
npm install
cp .env.example .env    # set VITE_API_BASE_URL to your deployed API URL
npm run dev
```

To seed the demo suite ("Customer Support Replies", 3 cases), see `backend/README.md`.

## Deploy to production

### 1. Deploy the backend (SAM)

```bash
./sam build
./sam deploy --guided \
  --parameter-overrides AmplifyDomain=https://main.dXXXXXX.amplifyapp.com
```

Follow the guided prompts. Stack name: `promptlens`.

### 2. Get the API endpoint

```bash
aws cloudformation describe-stacks --stack-name promptlens \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text
```

### 3. Deploy the frontend (Amplify)

1. Push this repo to GitHub
2. In the AWS Amplify console, connect the GitHub repo
3. Set the build environment variable `VITE_API_BASE_URL` to the API endpoint from step 2
4. Deploy — Amplify provides a public URL

### 5. Verify

```bash
curl <api-endpoint>/health
# Open the Amplify URL in a browser and run the seeded demo
```

## Architecture

See `docs/architecture.md` for the full diagram.

- **DynamoDB**: single-table design, PK/SK pattern (`SUITE#`, `CASE#`, `RUN#`)
- **Lambda**: Python 3.11, least-privilege IAM, synchronous run execution (max 3 cases)
- **API Gateway**: REST API with CORS (restricted to Amplify domain)
- **Bedrock**: prompt execution + rubric evaluation, invoked server-side only
- **CloudWatch**: structured logging (IDs, sizes, durations — no raw prompts/outputs)

## Cost & Security

- DynamoDB PAY_PER_REQUEST, Lambda/API per-request — dev/testing < $5/month
- No auth in MVP (post-MVP scope); no credentials in frontend
- CORS restricted to Amplify domain via `AmplifyDomain` template parameter
- Validation: prompts max 10,000 chars, temperature 0–1, maxTokens 1–4096, max 3 cases per run

## Cleanup

```bash
./sam delete --stack-name promptlens
```
