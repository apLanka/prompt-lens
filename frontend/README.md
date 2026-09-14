# PromptLens Frontend

React + TypeScript + Vite frontend for PromptLens, a prompt-regression testing tool.

## Setup

```bash
cd frontend
npm install
cp .env.example .env   # then set your deployed API URL
npm run dev
```

The dev server reads `VITE_API_BASE_URL` at build time (see `.env.example`).

## Screens

- `/` — Home: suite list, create suite
- `/suites/:suiteId/edit` — Suite Editor: rename suite, manage cases
- `/suites/:suiteId/run` — Run Config: prompts, model, settings, case selection (max 3)
- `/runs/:runId` — Results: summary cards, filters, side-by-side comparison

## Demo data

To seed the demo suite ("Customer Support Replies" with 3 cases), run against the configured table:

```bash
python -m src.handlers.api.seed
```

## Testing

```bash
npm run build   # type check + production build
npx vitest run  # unit tests (API client)
```

## Constraints

- No AWS credentials or Bedrock configuration in frontend code
- All model invocations go through the backend API
- MVP: 3 cases per run, 2 model options
