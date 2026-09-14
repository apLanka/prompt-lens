# PromptLens Backend

Python 3.11 Lambda + API Gateway + DynamoDB + Bedrock, deployed via AWS SAM.

## Setup

```bash
cd backend
python3.11 -m venv .venv        # or: uv venv --python 3.11 .venv
.venv/bin/pip install -r requirements.txt
```

## Test

Run from `backend/` (imports resolve via cwd):

```bash
.venv/bin/python -m pytest tests/ -q
```

## Deploy

From the repo root (the `sam` wrapper runs SAM inside `backend/`):

```bash
./sam build
./sam deploy --guided
```

Stack name: `promptlens`. Follow the guided prompts (region, CAPABILITY_IAM, etc.).

## Seed demo data

Run from `backend/` against the deployed table:

```bash
.venv/bin/python -m src.handlers.api.seed
```

Creates the "Customer Support Replies" demo suite with 3 cases.

## Layout

- `src/handlers/api/` — Lambda handler, routes, models, DynamoDB + Bedrock clients
- `tests/` — pytest suite (moto-mocked AWS)
- `template.yaml` — SAM template (single table, one function, REST API)
