# PromptLens

A lightweight prompt-regression testing workspace for AI engineers. Compares two prompt versions against saved test cases, invokes Amazon Bedrock models, scores results against rubrics, and highlights regressions.

## Repository layout

```
prompt-lens/
├── backend/    # Python 3.11 Lambda + SAM (API, DynamoDB, Bedrock)
├── frontend/   # React + TypeScript + Vite
├── docs/       # ADRs and implementation plans
└── sam         # SAM CLI wrapper (runs in backend/)
```

See `backend/README.md` and `frontend/README.md` for package-specific setup.

## Quickstart

**Backend** — test and deploy:

```bash
cd backend && .venv/bin/python -m pytest tests/ -q   # 183 tests
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

## Verify deployment

```bash
aws cloudformation describe-stacks --stack-name promptlens \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text

curl <api-endpoint>/health
```

## Architecture

- **DynamoDB**: single-table design, PK/SK pattern (`SUITE#`, `CASE#`, `RUN#`)
- **Lambda**: Python 3.11, least-privilege IAM, synchronous run execution (max 3 cases)
- **API Gateway**: REST API with CORS
- **Bedrock**: prompt execution + rubric evaluation, invoked server-side only

## Cost & Security

- DynamoDB PAY_PER_REQUEST, Lambda/API per-request — dev/testing < $5/month
- No auth in MVP (post-MVP scope); no credentials in frontend; CORS open until Feature 7 locks it to the Amplify domain

## Cleanup

```bash
./sam delete --stack-name promptlens
```
