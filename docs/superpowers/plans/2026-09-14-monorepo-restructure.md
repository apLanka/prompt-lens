# Monorepo Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure PromptLens into a clean two-package monorepo — `backend/` (Python SAM) and `frontend/` (React) — with root-level entrypoints, without breaking any test, build, or documented command.

**Architecture:** Plain two-directory layout (no Nx/Turborepo — overkill for 2 packages). Backend files move from repo root into `backend/`; frontend untouched. Root keeps shared context (README, CONTEXT.md, docs/) and a `./sam` wrapper that transparently runs SAM from `backend/`.

**Tech Stack:** git mv, AWS SAM, pytest, Vite (unchanged)

**Spec:** User request: "restructure — create user friendly structure"

## Global Constraints

- Zero behavior change: 183 backend tests, 6 frontend tests, `./sam validate --lint` must all pass after the move
- Use `git mv` for all tracked files (preserve history); plain `mv` only for untracked `.venv`
- Handler stays `src.handlers.api.handler`; `CodeUri: .` stays `.` (now relative to `backend/`)
- Tests MUST be run as `.venv/bin/python -m pytest tests/ -q` from `backend/` — imports rely on cwd being the directory that contains `src/` (this is how they work today; no conftest/path config exists)
- No reformatting/editing of moved source files — moves only, plus the specific edits this plan lists
- Every documented command in any README must work verbatim from where the README says to run it

## Current State (verified)

- Backend files at repo root: `src/`, `tests/`, `template.yaml`, `samconfig.toml`, `.samignore`, `sam` (wrapper, tracked), `.venv/` (untracked, NOT in .gitignore — only `venv/` is), `README.md`, `CONTEXT.md`
- `sam` wrapper content: `#!/bin/bash\nexec ~/.sam-cli-env/bin/sam "$@"` (SAM CLI lives in `~/.sam-cli-env` because Homebrew Python 3.14 broke it)
- `.samignore` entries (relative to CodeUri root): `.git/`, `README.md`, `template.yaml`, `docs/`, `.superpowers/`, `tests/`, `.claude/`, `*.md`, `.gitignore`, `.samignore`
- Root README documents `sam build` / `sam deploy --guided` from root, and `python -m src.handlers.api.seed`
- frontend/README.md "Demo data" section documents `python -m src.handlers.api.seed`
- `.gitignore` has `venv/` (NOT `.venv/`), `frontend/dist/`, `frontend/node_modules/`, `.aws-sam/`, `samconfig.toml` (note: samconfig.toml is gitignored yet currently TRACKED — leave that inconsistency alone)

## Target Structure

```
prompt-lens/
├── README.md          # root overview: what lives where, quickstart
├── CONTEXT.md         # unchanged
├── docs/              # unchanged (ADRs, plans)
├── .scratch/          # unchanged (wayfinder)
├── sam                # wrapper — now cds into backend/ before exec
├── backend/
│   ├── README.md      # NEW: backend dev/deploy/test/seed docs
│   ├── requirements.txt  # NEW: boto3, moto, pytest
│   ├── template.yaml
│   ├── samconfig.toml
│   ├── .samignore
│   ├── .venv/         # moved here (untracked)
│   ├── src/handlers/api/…
│   └── tests/
└── frontend/          # untouched except one README line
```

---

### Task 1: Physical Move and Wrapper Rewire

**Files:**
- Move (git mv): `src` → `backend/src`, `tests` → `backend/tests`, `template.yaml` → `backend/template.yaml`, `samconfig.toml` → `backend/samconfig.toml`, `.samignore` → `backend/.samignore`
- Move (plain mv, untracked): `.venv` → `backend/.venv`
- Modify: `sam` (root wrapper)
- Modify: `.gitignore` (root)
- Rewrite: `backend/.samignore`

**Interfaces:**
- Produces: backend/ containing the full deployable + testable Python package; root `./sam` still works from root

- [ ] **Step 1: Create backend/ and move tracked files**

```bash
cd /Users/pasindulanka/LANKA/Development/AWS/prompt-lens
mkdir backend
git mv src backend/src
git mv tests backend/tests
git mv template.yaml backend/template.yaml
git mv samconfig.toml backend/samconfig.toml
git mv .samignore backend/.samignore
```

- [ ] **Step 2: Move the untracked venv**

```bash
mv .venv backend/.venv
```

- [ ] **Step 3: Rewrite the root sam wrapper to run from backend/**

Replace the entire content of `sam` with:

```bash
#!/bin/bash
# SAM CLI wrapper — runs SAM from backend/ (template + code live there).
# SAM CLI itself lives in ~/.sam-cli-env (Homebrew Python 3.14 is broken).
cd "$(dirname "$0")/backend" || exit 1
exec ~/.sam-cli-env/bin/sam "$@"
```

- [ ] **Step 4: Rewrite backend/.samignore for the new CodeUri root**

Replace `backend/.samignore` content with:

```
# SAM build exclusions (relative to backend/)
.git/
README.md
requirements.txt
template.yaml
tests/
.venv/
__pycache__/
*.pyc
.samignore
.pytest_cache/
```

(Removed `docs/`, `.superpowers/`, `.claude/`, `*.md`, `.gitignore` — none of those exist inside backend/ except README.md which is listed explicitly; added `.venv/`, `__pycache__/`, `.pytest_cache/` which now do.)

- [ ] **Step 5: Update root .gitignore**

Add a Python venv/caches section (keep all existing lines):

```
# Python venv & caches
.venv/
.pytest_cache/
__pycache__/
```

(`.venv/` pattern matches `backend/.venv/` too. Leave the existing `samconfig.toml` line untouched — out of scope.)

- [ ] **Step 6: Verify from the new location**

```bash
cd backend && .venv/bin/python -m pytest tests/ -q
```
Expected: 183 passed.

```bash
cd /Users/pasindulanka/LANKA/Development/AWS/prompt-lens && ./sam validate --lint 2>&1 | grep -v -i telemetry
```
Expected: ".../backend/template.yaml is a valid SAM Template"

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor: move backend into backend/ for monorepo layout"
```

---

### Task 2: Docs and Requirements for the New Layout

**Files:**
- Create: `backend/README.md`
- Create: `backend/requirements.txt`
- Modify: `README.md` (root)
- Modify: `frontend/README.md` (one line)

**Interfaces:**
- Consumes: new layout from Task 1
- Produces: every documented command runnable verbatim; reproducible backend deps

- [ ] **Step 1: Create backend/requirements.txt**

```
boto3>=1.43
moto>=5.2
pytest>=9.0
```

(These are the exact packages in the working venv: boto3 1.43.93, moto 5.2.3, pytest 9.1.1.)

- [ ] **Step 2: Create backend/README.md**

```markdown
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
```

- [ ] **Step 3: Update root README.md**

Replace the entire root `README.md` with a monorepo-oriented version:

```markdown
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
```

- [ ] **Step 4: Fix the seed line in frontend/README.md**

In `frontend/README.md` Demo data section, change:

```
python src/handlers/api/seed.py
```

Wait — the current line reads `python -m src.handlers.api.seed` (corrected in a prior fix). Either way, it only works from `backend/`. Replace the Demo data section's command line and its lead-in so it reads:

```markdown
## Demo data

To seed the demo suite ("Customer Support Replies" with 3 cases), run from `backend/`:

```bash
cd ../backend && .venv/bin/python -m src.handlers.api.seed
```
```

(Match the surrounding heading style exactly; keep all other README content unchanged.)

- [ ] **Step 5: Full verification pass**

```bash
cd /Users/pasindulanka/LANKA/Development/AWS/prompt-lens/backend && .venv/bin/python -m pytest tests/ -q
```
Expected: 183 passed

```bash
cd /Users/pasindulanka/LANKA/Development/AWS/prompt-lens && ./sam validate --lint 2>&1 | grep -v -i telemetry
```
Expected: valid SAM Template (path should show backend/template.yaml)

```bash
cd /Users/pasindulanka/LANKA/Development/AWS/prompt-lens/frontend && npm run build && npx vitest run
```
Expected: build clean, 6/6 tests

```bash
cd /Users/pasindulanka/LANKA/Development/AWS/prompt-lens && git status --short
```
Expected: only the intended changes staged/committed; nothing from `backend/.venv` tracked

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "docs: monorepo layout — backend README, requirements, root quickstart"
```

---

## Self-Review Checklist

- [x] All moves are `git mv` (history-preserving) except untracked `.venv`
- [x] Every command in every README verified by a step that runs it (or an equivalent check) — nothing documented that isn't tested
- [x] Root `./sam` wrapper works from root (validate step proves template resolution through backend/)
- [x] `.samignore` rewritten only for entries that exist relative to `backend/`
- [x] `.gitignore` gains `.venv/` (currently only `venv/` — real gap found during planning)
- [x] frontend/ untouched except its README seed line
- [x] No source file content edits — moves and the named files only
