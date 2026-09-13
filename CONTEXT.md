# PromptLens Context

PromptLens is a lightweight prompt-regression testing workspace for AI engineers. It compares two prompt versions against saved test cases, invokes Amazon Bedrock models, scores results against rubrics, and highlights regressions.

## Language

### Core Entities

**Suite**:
A named collection of test cases that share a common testing purpose (e.g., "Customer-support replies"). Contains metadata (name, timestamps) and owns its cases.
_Avoid_: TestSuite, SuiteGroup, Collection

**Case** (Test Case):
An individual test scenario with an input prompt, optional expected behavior description, optional tags, and a stable case ID. Belongs to exactly one Suite.
_Avoid_: TestCase, Scenario, Example, Prompt

**Run**:
A comparison execution that tests baseline and candidate prompts against selected cases from a Suite. Stores configuration (model, temperature, tokens, rubric), status, and produces Run-Case Results.
_Aavoid_: Execution, Comparison, TestRun, Evaluation

**Run-Case Result**:
The outcome of evaluating a specific Case within a Run. Contains baseline output, candidate output, scores, rationales, latency, and classification status.
_Aavoid_: Result, CaseResult, EvaluationResult

### Prompts and Evaluation

**Prompt**:
The text content of a baseline or candidate prompt. Not stored as a separate entity; embedded within Run configuration.
_Aavoid_: PromptText, Template, Instruction

**Model**:
An Amazon Bedrock foundation model used for generating outputs (baseline/candidate) or evaluating results. Identified by model ID; may use an alias for UI display.
_Aavoid_: FoundationModel, LLM, AIModel

**Rubric**:
Natural-language evaluation criteria that the Evaluator uses to score outputs. Stored as plain text within a Run.
_Aavoid_: Criteria, ScoringCriteria, EvaluationPrompt

**Evaluator**:
The scoring mechanism that assesses outputs against a Rubric. Implemented as a Bedrock invocation with strict JSON response schema.
_Aavoid_: Scorer, Assessor, Judge

### Status and Classification

**Classification**:
The status assigned to a Run-Case Result based on score comparison: Improved, Regressed, Unchanged, Needs review, or Failed.
_Aavoid_: Status, ResultStatus, Outcome

**Confidence**:
The Evaluator's self-assessed certainty in its scoring (high/medium/low). Low confidence triggers Needs review classification.
_Aavoid_: Certainty, Assurance

### Infrastructure

**Suite**:
Part of Suite Management context.
**Run**:
Part of Run Execution context.
**Case**:
Shared between Suite Management and Run Execution contexts.
**Run-Case Result**:
Part of Evaluation context.

## Rules

- A Suite owns Cases; Cases cannot exist without a Suite
- A Run references a Suite but does not own it; Runs can reference the same Suite independently
- Run-Case Results are created by Runs and reference Cases; they are not shared between Runs
- Prompts are embedded in Run configuration, not stored as separate entities
- Model IDs are server-configured and allowlisted; users select from permitted options
- Evaluator responses must conform to strict JSON schema; malformed results are marked Needs review
- Scores are clamped to 1-5 range; out-of-range values are normalized
- A Run's status progresses: RUNNING → COMPLETED | PARTIAL | FAILED
- Individual Case failures do not fail the entire Run
