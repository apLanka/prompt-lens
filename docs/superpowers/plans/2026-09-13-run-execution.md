# Run Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the comparison run orchestration that takes baseline and candidate prompts, executes them against selected cases using Bedrock, and stores results. Includes synchronous processing for up to 3 cases.

**Architecture:** Extend the Lambda handler with route-based request handling for Run operations. Use DynamoDB single-table design with PK/SK pattern for efficient queries. Each operation validates input and returns structured JSON responses. Bedrock invocations are synchronous and include evaluator scoring with strict JSON schema validation.

**Tech Stack:** Python 3.11, boto3 (DynamoDB + Bedrock), AWS Lambda, API Gateway

**Spec:** [Feature 3 Ticket](../../.scratch/wayfinder/tickets/03-run-execution.md)

## Global Constraints

- DynamoDB table name: PromptLens
- Run PK = `RUN#{runId}`, SK = `META`
- Run-Case Result PK = `RUN#{runId}`, SK = `CASE#{caseId}`
- Run IDs are generated (UUID4)
- Timestamps use ISO 8601 format
- All responses include CORS headers
- Input validation required for all operations
- Maximum 3 cases per run (MVP constraint)
- Scores clamped to 1-5 range; out-of-range values normalized
- Malformed evaluator responses marked as "Needs review"
- Individual case failures don't fail entire run

---

## File Structure

```
prompt-lens/
├── src/
│   └── handlers/
│       └── api/
│           ├── __init__.py              # Main handler (modify)
│           ├── routes/
│           │   ├── __init__.py          # Route dispatcher (modify)
│           │   ├── suites.py            # Suite CRUD operations (existing)
│           │   ├── cases.py             # Case CRUD operations (existing)
│           │   └── runs.py              # Run CRUD operations (create)
│           ├── models/
│           │   ├── __init__.py          # Models package (modify)
│           │   ├── suite.py             # Suite data model (existing)
│           │   ├── case.py              # Case data model (existing)
│           │   ├── run.py               # Run data model (create)
│           │   └── run_case_result.py   # Run-Case Result data model (create)
│           ├── dynamodb.py              # DynamoDB operations (modify)
│           ├── bedrock.py               # Bedrock operations (create)
│           └── seed.py                  # Seed data (existing)
├── tests/
│   └── handlers/
│       └── api/
│           ├── __init__.py              # Test package (existing)
│           ├── test_suites.py           # Suite tests (existing)
│           ├── test_cases.py            # Case tests (existing)
│           └── test_runs.py             # Run tests (create)
└── template.yaml                        # No changes needed
```

---

## Task 1: Create Run and Run-Case Result Data Models

**Files:**
- Create: `src/handlers/api/models/run.py`
- Create: `src/handlers/api/models/run_case_result.py`
- Modify: `src/handlers/api/models/__init__.py`

**Interfaces:**
- Consumes: None (initial models)
- Produces: Run and RunCaseResult dataclasses for use by routes and DynamoDB operations

- [ ] **Step 1: Create Run model**

Create `src/handlers/api/models/run.py`:

```python
"""Run data model."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional
import uuid


@dataclass
class Run:
    """A comparison execution that tests baseline and candidate prompts against selected cases."""
    
    suite_id: str
    model_id: str
    baseline_prompt: str
    candidate_prompt: str
    rubric: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "RUNNING"  # RUNNING, COMPLETED, PARTIAL, FAILED
    temperature: float = 0.7
    max_tokens: int = 1024
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for DynamoDB storage."""
        result = {
            "run_id": self.run_id,
            "suite_id": self.suite_id,
            "model_id": self.model_id,
            "baseline_prompt": self.baseline_prompt,
            "candidate_prompt": self.candidate_prompt,
            "rubric": self.rubric,
            "status": self.status,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "created_at": self.created_at,
        }
        if self.completed_at:
            result["completed_at"] = self.completed_at
        return result
    
    def to_response(self) -> dict:
        """Convert to API response format."""
        result = {
            "runId": self.run_id,
            "suiteId": self.suite_id,
            "modelId": self.model_id,
            "baselinePrompt": self.baseline_prompt,
            "candidatePrompt": self.candidate_prompt,
            "rubric": self.rubric,
            "status": self.status,
            "temperature": self.temperature,
            "maxTokens": self.max_tokens,
            "createdAt": self.created_at,
        }
        if self.completed_at:
            result["completedAt"] = self.completed_at
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Run':
        """Create Run from DynamoDB item."""
        return cls(
            run_id=data["run_id"],
            suite_id=data["suite_id"],
            model_id=data["model_id"],
            baseline_prompt=data["baseline_prompt"],
            candidate_prompt=data["candidate_prompt"],
            rubric=data["rubric"],
            status=data.get("status", "RUNNING"),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 1024),
            created_at=data["created_at"],
            completed_at=data.get("completed_at"),
        )
```

- [ ] **Step 2: Create Run-Case Result model**

Create `src/handlers/api/models/run_case_result.py`:

```python
"""Run-Case Result data model."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RunCaseResult:
    """The outcome of evaluating a specific Case within a Run."""
    
    run_id: str
    case_id: str
    baseline_output: Optional[str] = None
    candidate_output: Optional[str] = None
    baseline_score: Optional[int] = None
    candidate_score: Optional[int] = None
    baseline_rationale: Optional[str] = None
    candidate_rationale: Optional[str] = None
    baseline_latency_ms: Optional[float] = None
    candidate_latency_ms: Optional[float] = None
    classification: str = "Needs review"  # Improved, Regressed, Unchanged, Needs review, Failed
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for DynamoDB storage."""
        result = {
            "run_id": self.run_id,
            "case_id": self.case_id,
            "classification": self.classification,
        }
        if self.baseline_output is not None:
            result["baseline_output"] = self.baseline_output
        if self.candidate_output is not None:
            result["candidate_output"] = self.candidate_output
        if self.baseline_score is not None:
            result["baseline_score"] = self.baseline_score
        if self.candidate_score is not None:
            result["candidate_score"] = self.candidate_score
        if self.baseline_rationale is not None:
            result["baseline_rationale"] = self.baseline_rationale
        if self.candidate_rationale is not None:
            result["candidate_rationale"] = self.candidate_rationale
        if self.baseline_latency_ms is not None:
            result["baseline_latency_ms"] = self.baseline_latency_ms
        if self.candidate_latency_ms is not None:
            result["candidate_latency_ms"] = self.candidate_latency_ms
        if self.error is not None:
            result["error"] = self.error
        return result
    
    def to_response(self) -> dict:
        """Convert to API response format."""
        result = {
            "runId": self.run_id,
            "caseId": self.case_id,
            "classification": self.classification,
        }
        if self.baseline_output is not None:
            result["baselineOutput"] = self.baseline_output
        if self.candidate_output is not None:
            result["candidateOutput"] = self.candidate_output
        if self.baseline_score is not None:
            result["baselineScore"] = self.baseline_score
        if self.candidate_score is not None:
            result["candidateScore"] = self.candidate_score
        if self.baseline_rationale is not None:
            result["baselineRationale"] = self.baseline_rationale
        if self.candidate_rationale is not None:
            result["candidateRationale"] = self.candidate_rationale
        if self.baseline_latency_ms is not None:
            result["baselineLatencyMs"] = self.baseline_latency_ms
        if self.candidate_latency_ms is not None:
            result["candidateLatencyMs"] = self.candidate_latency_ms
        if self.error is not None:
            result["error"] = self.error
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RunCaseResult':
        """Create RunCaseResult from DynamoDB item."""
        return cls(
            run_id=data["run_id"],
            case_id=data["case_id"],
            baseline_output=data.get("baseline_output"),
            candidate_output=data.get("candidate_output"),
            baseline_score=data.get("baseline_score"),
            candidate_score=data.get("candidate_score"),
            baseline_rationale=data.get("baseline_rationale"),
            candidate_rationale=data.get("candidate_rationale"),
            baseline_latency_ms=data.get("baseline_latency_ms"),
            candidate_latency_ms=data.get("candidate_latency_ms"),
            classification=data.get("classification", "Needs review"),
            error=data.get("error"),
        )
```

- [ ] **Step 3: Update models __init__.py**

Modify `src/handlers/api/models/__init__.py` to export new models:

```python
"""Data models for PromptLens API."""

from .suite import Suite
from .case import Case
from .run import Run
from .run_case_result import RunCaseResult

__all__ = ["Suite", "Case", "Run", "RunCaseResult"]
```

- [ ] **Step 4: Commit**

```bash
git add src/handlers/api/models/run.py src/handlers/api/models/run_case_result.py src/handlers/api/models/__init__.py
git commit -m "feat: add Run and RunCaseResult data models"
```

---

## Task 2: Create DynamoDB Operations for Runs

**Files:**
- Modify: `src/handlers/api/dynamodb.py`

**Interfaces:**
- Consumes: Run, RunCaseResult models
- Produces: DynamoDB operations for Run CRUD

- [ ] **Step 1: Add Run DynamoDB operations**

Append to `src/handlers/api/dynamodb.py`:

```python
from .models import Run, RunCaseResult


def create_run(run: Run) -> Run:
    """Create a new run in DynamoDB."""
    table = get_table()
    
    table.put_item(
        Item={
            "PK": f"RUN#{run.run_id}",
            "SK": "META",
            "run_id": run.run_id,
            "suite_id": run.suite_id,
            "model_id": run.model_id,
            "baseline_prompt": run.baseline_prompt,
            "candidate_prompt": run.candidate_prompt,
            "rubric": run.rubric,
            "status": run.status,
            "temperature": run.temperature,
            "max_tokens": run.max_tokens,
            "created_at": run.created_at,
        }
    )
    
    return run


def get_run(run_id: str) -> Optional[Run]:
    """Get a run by ID."""
    table = get_table()
    
    response = table.get_item(
        Key={
            "PK": f"RUN#{run_id}",
            "SK": "META",
        }
    )
    
    item = response.get("Item")
    if not item:
        return None
    
    return Run(
        run_id=item["run_id"],
        suite_id=item["suite_id"],
        model_id=item["model_id"],
        baseline_prompt=item["baseline_prompt"],
        candidate_prompt=item["candidate_prompt"],
        rubric=item["rubric"],
        status=item.get("status", "RUNNING"),
        temperature=item.get("temperature", 0.7),
        max_tokens=item.get("max_tokens", 1024),
        created_at=item["created_at"],
        completed_at=item.get("completed_at"),
    )


def list_runs() -> List[Run]:
    """List all runs."""
    table = get_table()
    
    items: List[dict] = []
    response = table.query(
        IndexName="SK-index",
        KeyConditionExpression=Key("SK").eq("META"),
    )
    items.extend(response.get("Items", []))
    
    while "LastEvaluatedKey" in response:
        response = table.query(
            IndexName="SK-index",
            KeyConditionExpression=Key("SK").eq("META"),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))
    
    return [
        Run(
            run_id=item["run_id"],
            suite_id=item["suite_id"],
            model_id=item["model_id"],
            baseline_prompt=item["baseline_prompt"],
            candidate_prompt=item["candidate_prompt"],
            rubric=item["rubric"],
            status=item.get("status", "RUNNING"),
            temperature=item.get("temperature", 0.7),
            max_tokens=item.get("max_tokens", 1024),
            created_at=item["created_at"],
            completed_at=item.get("completed_at"),
        )
        for item in items if item.get("PK", "").startswith("RUN#")
    ]


def update_run_status(run_id: str, status: str) -> Optional[Run]:
    """Update run status."""
    table = get_table()
    
    update_expr = "SET #status = :status"
    expr_names = {"#status": "status"}
    expr_values = {":status": status}
    
    if status in ["COMPLETED", "PARTIAL", "FAILED"]:
        update_expr += ", completed_at = :completed_at"
        expr_values[":completed_at"] = datetime.now(timezone.utc).isoformat()
    
    response = table.update_item(
        Key={
            "PK": f"RUN#{run_id}",
            "SK": "META",
        },
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
        ReturnValues="ALL_NEW",
    )
    
    attributes = response.get("Attributes", {})
    return Run(
        run_id=attributes["run_id"],
        suite_id=attributes["suite_id"],
        model_id=attributes["model_id"],
        baseline_prompt=attributes["baseline_prompt"],
        candidate_prompt=attributes["candidate_prompt"],
        rubric=attributes["rubric"],
        status=attributes.get("status", "RUNNING"),
        temperature=attributes.get("temperature", 0.7),
        max_tokens=attributes.get("max_tokens", 1024),
        created_at=attributes["created_at"],
        completed_at=attributes.get("completed_at"),
    )


def create_run_case_result(result: RunCaseResult) -> RunCaseResult:
    """Create a new run-case result in DynamoDB."""
    table = get_table()
    
    item = {
        "PK": f"RUN#{result.run_id}",
        "SK": f"CASE#{result.case_id}",
        "run_id": result.run_id,
        "case_id": result.case_id,
        "classification": result.classification,
    }
    
    if result.baseline_output is not None:
        item["baseline_output"] = result.baseline_output
    if result.candidate_output is not None:
        item["candidate_output"] = result.candidate_output
    if result.baseline_score is not None:
        item["baseline_score"] = result.baseline_score
    if result.candidate_score is not None:
        item["candidate_score"] = result.candidate_score
    if result.baseline_rationale is not None:
        item["baseline_rationale"] = result.baseline_rationale
    if result.candidate_rationale is not None:
        item["candidate_rationale"] = result.candidate_rationale
    if result.baseline_latency_ms is not None:
        item["baseline_latency_ms"] = result.baseline_latency_ms
    if result.candidate_latency_ms is not None:
        item["candidate_latency_ms"] = result.candidate_latency_ms
    if result.error is not None:
        item["error"] = result.error
    
    table.put_item(Item=item)
    
    return result


def get_run_case_results(run_id: str) -> List[RunCaseResult]:
    """Get all case results for a run."""
    table = get_table()
    
    items: List[dict] = []
    response = table.query(
        KeyConditionExpression=Key("PK").eq(f"RUN#{run_id}")
        & Key("SK").begins_with("CASE#"),
    )
    items.extend(response.get("Items", []))
    
    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=Key("PK").eq(f"RUN#{run_id}")
            & Key("SK").begins_with("CASE#"),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))
    
    return [
        RunCaseResult(
            run_id=item["run_id"],
            case_id=item["case_id"],
            baseline_output=item.get("baseline_output"),
            candidate_output=item.get("candidate_output"),
            baseline_score=item.get("baseline_score"),
            candidate_score=item.get("candidate_score"),
            baseline_rationale=item.get("baseline_rationale"),
            candidate_rationale=item.get("candidate_rationale"),
            baseline_latency_ms=item.get("baseline_latency_ms"),
            candidate_latency_ms=item.get("candidate_latency_ms"),
            classification=item.get("classification", "Needs review"),
            error=item.get("error"),
        )
        for item in items
    ]


def delete_run(run_id: str) -> bool:
    """Delete run and all its case results."""
    table = get_table()
    
    # First, get all items for this run
    response = table.query(
        KeyConditionExpression=Key("PK").eq(f"RUN#{run_id}"),
    )
    
    # Delete run metadata and all case results
    with table.batch_writer() as batch:
        for item in response.get("Items", []):
            batch.delete_item(
                Key={
                    "PK": item["PK"],
                    "SK": item["SK"],
                }
            )
    
    return True
```

- [ ] **Step 2: Commit**

```bash
git add src/handlers/api/dynamodb.py
git commit -m "feat: add DynamoDB operations for Run and RunCaseResult CRUD"
```

---

## Task 3: Create Bedrock Operations Module

**Files:**
- Create: `src/handlers/api/bedrock.py`

**Interfaces:**
- Consumes: Bedrock SDK
- Produces: Bedrock invocation operations for prompts and evaluation

- [ ] **Step 1: Create Bedrock operations module**

Create `src/handlers/api/bedrock.py`:

```python
"""Bedrock operations for prompt invocation and evaluation."""

import json
import os
import time
from typing import Tuple, Optional
import boto3
from botocore.exceptions import ClientError


def get_bedrock_client():
    """Get Bedrock runtime client."""
    return boto3.client("bedrock-runtime")


def invoke_model(
    model_id: str,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Tuple[str, float]:
    """Invoke a Bedrock model and return output with latency.
    
    Args:
        model_id: Bedrock model ID
        prompt: Input prompt
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        
    Returns:
        Tuple of (output_text, latency_ms)
        
    Raises:
        ClientError: If Bedrock invocation fails
    """
    client = get_bedrock_client()
    
    start_time = time.time()
    
    # Prepare request body based on model type
    if "claude" in model_id.lower():
        body = json.dumps({
            "prompt": prompt,
            "max_tokens_to_sample": max_tokens,
            "temperature": temperature,
        })
        content_type = "application/json"
        accept = "application/json"
    else:
        # Default to Claude-like format for other models
        body = json.dumps({
            "prompt": prompt,
            "max_tokens_to_sample": max_tokens,
            "temperature": temperature,
        })
        content_type = "application/json"
        accept = "application/json"
    
    response = client.invoke_model(
        modelId=model_id,
        body=body,
        contentType=content_type,
        accept=accept,
    )
    
    latency_ms = (time.time() - start_time) * 1000
    
    response_body = json.loads(response["body"].read())
    
    # Extract text based on model type
    if "claude" in model_id.lower():
        output_text = response_body.get("completion", "")
    else:
        output_text = response_body.get("generation", "")
    
    return output_text, latency_ms


def evaluate_output(
    output: str,
    rubric: str,
    model_id: str,
    temperature: float = 0.3,
) -> dict:
    """Evaluate output against rubric using Bedrock.
    
    Args:
        output: The output to evaluate
        rubric: Evaluation criteria
        model_id: Bedrock model ID for evaluation
        temperature: Sampling temperature (lower for more consistent scoring)
        
    Returns:
        Dictionary with score, confidence, rationale, violations
        
    Raises:
        ValueError: If response cannot be parsed
    """
    client = get_bedrock_client()
    
    evaluation_prompt = f"""You are an expert evaluator. Score the following output based on the rubric.

Output to evaluate:
{output}

Evaluation rubric:
{rubric}

Provide your evaluation as a JSON object with exactly these fields:
- "score": an integer from 1 to 5 (1=poor, 5=excellent)
- "confidence": "high", "medium", or "low"
- "rationale": a brief explanation of your scoring
- "violations": an array of specific rubric violations (empty array if none)

Respond ONLY with the JSON object, no other text."""
    
    # Prepare request body
    if "claude" in model_id.lower():
        body = json.dumps({
            "prompt": evaluation_prompt,
            "max_tokens_to_sample": 1024,
            "temperature": temperature,
        })
    else:
        body = json.dumps({
            "prompt": evaluation_prompt,
            "max_tokens_to_sample": 1024,
            "temperature": temperature,
        })
    
    response = client.invoke_model(
        modelId=model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    
    response_body = json.loads(response["body"].read())
    
    # Extract text based on model type
    if "claude" in model_id.lower():
        response_text = response_body.get("completion", "")
    else:
        response_text = response_body.get("generation", "")
    
    # Parse JSON response
    try:
        # Try to extract JSON from response (may be wrapped in markdown)
        json_match = response_text.strip()
        if "```json" in json_match:
            json_match = json_match.split("```json")[1].split("```")[0]
        elif "```" in json_match:
            json_match = json_match.split("```")[1].split("```")[0]
        
        evaluation = json.loads(json_match)
        
        # Validate and clamp score
        score = evaluation.get("score", 3)
        if not isinstance(score, (int, float)):
            score = 3
        score = max(1, min(5, int(score)))
        
        # Validate confidence
        confidence = evaluation.get("confidence", "low")
        if confidence not in ["high", "medium", "low"]:
            confidence = "low"
        
        return {
            "score": score,
            "confidence": confidence,
            "rationale": evaluation.get("rationale", "No rationale provided"),
            "violations": evaluation.get("violations", []),
        }
    except (json.JSONDecodeError, KeyError, TypeError):
        # Malformed response - return default "Needs review" scoring
        return {
            "score": 3,
            "confidence": "low",
            "rationale": "Unable to parse evaluator response",
            "violations": [],
        }


def classify_result(baseline_score: int, candidate_score: int) -> str:
    """Classify result based on score comparison.
    
    Args:
        baseline_score: Score for baseline output (1-5)
        candidate_score: Score for candidate output (1-5)
        
    Returns:
        Classification string
    """
    if candidate_score > baseline_score:
        return "Improved"
    elif candidate_score < baseline_score:
        return "Regressed"
    else:
        return "Unchanged"
```

- [ ] **Step 2: Commit**

```bash
git add src/handlers/api/bedrock.py
git commit -m "feat: add Bedrock operations for prompt invocation and evaluation"
```

---

## Task 4: Create Run Route Handlers

**Files:**
- Create: `src/handlers/api/routes/runs.py`
- Modify: `src/handlers/api/routes/__init__.py`

**Interfaces:**
- Consumes: DynamoDB operations, Bedrock operations
- Produces: Route handlers for Run API

- [ ] **Step 1: Create Run route handlers**

Create `src/handlers/api/routes/runs.py`:

```python
"""Run route handlers."""

import json
from typing import Any, Dict

from ..models import Run, RunCaseResult
from ..dynamodb import (
    create_run,
    get_run,
    list_runs,
    update_run_status,
    create_run_case_result,
    get_run_case_results,
    get_suite,
    get_cases,
)
from ..bedrock import invoke_model, evaluate_output, classify_result


MAX_CASES_PER_RUN = 3


def handle_runs(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle /runs routes."""
    method = event.get("httpMethod")
    
    if method == "GET":
        return list_runs_handler()
    elif method == "POST":
        return create_run_handler(event)
    else:
        return {
            "statusCode": 405,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Method not allowed"}),
        }


def handle_run_by_id(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle /runs/{runId} routes."""
    method = event.get("httpMethod")
    run_id = event.get("pathParameters", {}).get("runId")
    
    if not run_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "runId is required"}),
        }
    
    if method == "GET":
        return get_run_handler(run_id)
    elif method == "DELETE":
        return delete_run_handler(run_id)
    else:
        return {
            "statusCode": 405,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Method not allowed"}),
        }


def list_runs_handler() -> Dict[str, Any]:
    """List all runs."""
    runs = list_runs()
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps([r.to_response() for r in runs]),
    }


def create_run_handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """Create and execute a new run."""
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Invalid JSON"}),
        }
    
    # Validate required fields
    suite_id = body.get("suiteId")
    model_id = body.get("modelId")
    baseline_prompt = body.get("baselinePrompt")
    candidate_prompt = body.get("candidatePrompt")
    rubric = body.get("rubric")
    
    if not all([suite_id, model_id, baseline_prompt, candidate_prompt, rubric]):
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "suiteId, modelId, baselinePrompt, candidatePrompt, and rubric are required"}),
        }
    
    # Verify suite exists
    suite = get_suite(suite_id)
    if not suite:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Suite not found"}),
        }
    
    # Get cases (limit to MAX_CASES_PER_RUN)
    cases = get_cases(suite_id)[:MAX_CASES_PER_RUN]
    if not cases:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Suite has no cases"}),
        }
    
    # Create run
    run = Run(
        suite_id=suite_id,
        model_id=model_id,
        baseline_prompt=baseline_prompt,
        candidate_prompt=candidate_prompt,
        rubric=rubric,
        temperature=body.get("temperature", 0.7),
        max_tokens=body.get("maxTokens", 1024),
    )
    
    created_run = create_run(run)
    
    # Execute run asynchronously (in a real implementation, this would be async)
    # For MVP, we execute synchronously and return results
    try:
        execute_run(created_run, cases)
        run = get_run(run.run_id)
    except Exception as e:
        update_run_status(run.run_id, "FAILED")
        run = get_run(run.run_id)
    
    return {
        "statusCode": 201,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(run.to_response()),
    }


def get_run_handler(run_id: str) -> Dict[str, Any]:
    """Get a run with its results."""
    run = get_run(run_id)
    if not run:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Run not found"}),
        }
    
    results = get_run_case_results(run_id)
    response = run.to_response()
    response["results"] = [r.to_response() for r in results]
    
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(response),
    }


def delete_run_handler(run_id: str) -> Dict[str, Any]:
    """Delete a run and all its results."""
    run = get_run(run_id)
    if not run:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Run not found"}),
        }
    
    from ..dynamodb import delete_run
    delete_run(run_id)
    
    return {
        "statusCode": 204,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": "",
    }


def execute_run(run: Run, cases: list) -> None:
    """Execute a run against cases.
    
    Args:
        run: The run to execute
        cases: List of cases to test
    """
    successful_results = 0
    total_cases = len(cases)
    
    for case in cases:
        try:
            # Execute baseline prompt
            baseline_output, baseline_latency = invoke_model(
                model_id=run.model_id,
                prompt=f"{run.baseline_prompt}\n\n{case.input}",
                temperature=run.temperature,
                max_tokens=run.max_tokens,
            )
            
            # Execute candidate prompt
            candidate_output, candidate_latency = invoke_model(
                model_id=run.model_id,
                prompt=f"{run.candidate_prompt}\n\n{case.input}",
                temperature=run.temperature,
                max_tokens=run.max_tokens,
            )
            
            # Evaluate baseline output
            baseline_eval = evaluate_output(
                output=baseline_output,
                rubric=run.rubric,
                model_id=run.model_id,
            )
            
            # Evaluate candidate output
            candidate_eval = evaluate_output(
                output=candidate_output,
                rubric=run.rubric,
                model_id=run.model_id,
            )
            
            # Classify result
            classification = classify_result(
                baseline_score=baseline_eval["score"],
                candidate_score=candidate_eval["score"],
            )
            
            # Create result
            result = RunCaseResult(
                run_id=run.run_id,
                case_id=case.case_id,
                baseline_output=baseline_output,
                candidate_output=candidate_output,
                baseline_score=baseline_eval["score"],
                candidate_score=candidate_eval["score"],
                baseline_rationale=baseline_eval["rationale"],
                candidate_rationale=candidate_eval["rationale"],
                baseline_latency_ms=baseline_latency,
                candidate_latency_ms=candidate_latency,
                classification=classification,
            )
            
            create_run_case_result(result)
            successful_results += 1
            
        except Exception as e:
            # Individual case failure doesn't fail entire run
            result = RunCaseResult(
                run_id=run.run_id,
                case_id=case.case_id,
                error=str(e),
                classification="Failed",
            )
            create_run_case_result(result)
    
    # Update run status based on results
    if successful_results == total_cases:
        update_run_status(run.run_id, "COMPLETED")
    elif successful_results > 0:
        update_run_status(run.run_id, "PARTIAL")
    else:
        update_run_status(run.run_id, "FAILED")
```

- [ ] **Step 2: Update routes __init__.py**

Modify `src/handlers/api/routes/__init__.py` to export Run handlers:

```python
"""API route handlers."""

from .suites import handle_suites, handle_suite_by_id
from .cases import handle_cases, handle_case_by_id
from .runs import handle_runs, handle_run_by_id

__all__ = ["handle_suites", "handle_suite_by_id", "handle_cases", "handle_case_by_id", "handle_runs", "handle_run_by_id"]
```

- [ ] **Step 3: Commit**

```bash
git add src/handlers/api/routes/runs.py src/handlers/api/routes/__init__.py
git commit -m "feat: add Run route handlers with Bedrock execution"
```

---

## Task 5: Update Main Handler with Run Routes

**Files:**
- Modify: `src/handlers/api/__init__.py`

**Interfaces:**
- Consumes: Run route handlers
- Produces: Updated main handler with Run routing

- [ ] **Step 1: Add Run routes to main handler**

Modify `src/handlers/api/__init__.py` to add Run routes:

```python
"""PromptLens API Lambda Handler."""

import json
import os
import re
from typing import Any, Dict

from .routes.suites import handle_suites, handle_suite_by_id
from .routes.cases import handle_cases, handle_case_by_id
from .routes.runs import handle_runs, handle_run_by_id


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for API requests.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    path = event.get("path", "")
    method = event.get("httpMethod", "")

    # Health check endpoint
    if path == "/health":
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "status": "healthy",
                    "table": os.environ.get("TABLE_NAME", "PromptLens"),
                }
            ),
        }

    # OPTIONS request for CORS
    if method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
            "body": "",
        }

    # Route matching
    # /runs/{runId}
    run_match = re.match(r"^/runs/([^/]+)$", path)
    if run_match:
        event_copy = {
            **event,
            "pathParameters": {
                "runId": run_match.group(1),
            },
        }
        return handle_run_by_id(event_copy)

    # /runs
    if path == "/runs":
        return handle_runs(event)

    # /suites/{suiteId}/cases/{caseId}
    case_match = re.match(r"^/suites/([^/]+)/cases/([^/]+)$", path)
    if case_match:
        event_copy = {
            **event,
            "pathParameters": {
                "suiteId": case_match.group(1),
                "caseId": case_match.group(2),
            },
        }
        return handle_case_by_id(event_copy)

    # /suites/{suiteId}/cases
    cases_match = re.match(r"^/suites/([^/]+)/cases$", path)
    if cases_match:
        event_copy = {**event, "pathParameters": {"suiteId": cases_match.group(1)}}
        return handle_cases(event_copy)

    # /suites/{suiteId}
    suite_match = re.match(r"^/suites/([^/]+)$", path)
    if suite_match:
        event_copy = {**event, "pathParameters": {"suiteId": suite_match.group(1)}}
        return handle_suite_by_id(event_copy)

    # /suites
    if path == "/suites":
        return handle_suites(event)

    # Default response for unimplemented routes
    return {
        "statusCode": 404,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(
            {
                "message": "Not found",
            }
        ),
    }
```

- [ ] **Step 2: Commit**

```bash
git add src/handlers/api/__init__.py
git commit -m "feat: add Run routes to main handler"
```

---

## Task 6: Create Tests for Run Operations

**Files:**
- Create: `tests/test_runs.py`

**Interfaces:**
- Consumes: All previous modules
- Produces: Test coverage for Run operations

- [ ] **Step 1: Create Run tests**

Create `tests/test_runs.py`:

```python
"""Tests for Run operations."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from moto import mock_aws
import boto3
from src.handlers.api.models import Run, RunCaseResult
from src.handlers.api.dynamodb import create_run, get_run, list_runs, update_run_status, create_run_case_result, get_run_case_results, delete_run


@pytest.fixture
def aws_setup():
    """Set up AWS mocks."""
    with mock_aws():
        # Create DynamoDB table
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="PromptLens",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        
        # Create GSI for listing
        table.create_index(
            IndexName="SK-index",
            KeySchema=[
                {"AttributeName": "SK", "KeyType": "HASH"},
            ],
            Projection={"ProjectionType": "ALL"},
        )
        
        yield table


class TestCreateRun:
    """Tests for create_run."""
    
    def test_create_run(self, aws_setup):
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            baseline_prompt="Be helpful",
            candidate_prompt="Be concise and helpful",
            rubric="Score on helpfulness and clarity",
        )
        
        result = create_run(run)
        
        assert result.run_id == run.run_id
        assert result.suite_id == "suite-1"
        assert result.status == "RUNNING"
    
    def test_create_run_verifies_dynamodb_item(self, aws_setup):
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            baseline_prompt="Be helpful",
            candidate_prompt="Be concise and helpful",
            rubric="Score on helpfulness and clarity",
        )
        
        create_run(run)
        
        table = aws_setup
        response = table.get_item(
            Key={"PK": f"RUN#{run.run_id}", "SK": "META"}
        )
        
        item = response.get("Item")
        assert item is not None
        assert item["suite_id"] == "suite-1"
        assert item["model_id"] == "anthropic.claude-3-sonnet-20240229-v1:0"


class TestGetRun:
    """Tests for get_run."""
    
    def test_get_existing_run(self, aws_setup):
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            baseline_prompt="Be helpful",
            candidate_prompt="Be concise and helpful",
            rubric="Score on helpfulness and clarity",
        )
        
        create_run(run)
        result = get_run(run.run_id)
        
        assert result is not None
        assert result.run_id == run.run_id
    
    def test_get_nonexistent_run(self, aws_setup):
        result = get_run("nonexistent")
        
        assert result is None


class TestListRuns:
    """Tests for list_runs."""
    
    def test_list_empty(self, aws_setup):
        result = list_runs()
        
        assert result == []
    
    def test_list_multiple_runs(self, aws_setup):
        run1 = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            baseline_prompt="Be helpful",
            candidate_prompt="Be concise and helpful",
            rubric="Score on helpfulness and clarity",
        )
        run2 = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            baseline_prompt="Be helpful",
            candidate_prompt="Be concise and helpful",
            rubric="Score on helpfulness and clarity",
        )
        
        create_run(run1)
        create_run(run2)
        
        result = list_runs()
        
        assert len(result) == 2


class TestUpdateRunStatus:
    """Tests for update_run_status."""
    
    def test_update_status_to_completed(self, aws_setup):
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            baseline_prompt="Be helpful",
            candidate_prompt="Be concise and helpful",
            rubric="Score on helpfulness and clarity",
        )
        
        create_run(run)
        result = update_run_status(run.run_id, "COMPLETED")
        
        assert result.status == "COMPLETED"
        assert result.completed_at is not None
    
    def test_update_status_to_failed(self, aws_setup):
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            baseline_prompt="Be helpful",
            candidate_prompt="Be concise and helpful",
            rubric="Score on helpfulness and clarity",
        )
        
        create_run(run)
        result = update_run_status(run.run_id, "FAILED")
        
        assert result.status == "FAILED"
        assert result.completed_at is not None


class TestCreateRunCaseResult:
    """Tests for create_run_case_result."""
    
    def test_create_result(self, aws_setup):
        result = RunCaseResult(
            run_id="run-1",
            case_id="case-1",
            baseline_output="Baseline text",
            candidate_output="Candidate text",
            baseline_score=4,
            candidate_score=5,
            baseline_rationale="Good",
            candidate_rationale="Excellent",
            baseline_latency_ms=1000.0,
            candidate_latency_ms=1200.0,
            classification="Improved",
        )
        
        created = create_run_case_result(result)
        
        assert created.run_id == "run-1"
        assert created.case_id == "case-1"
        assert created.classification == "Improved"
    
    def test_create_result_with_error(self, aws_setup):
        result = RunCaseResult(
            run_id="run-1",
            case_id="case-1",
            error="Model invocation failed",
            classification="Failed",
        )
        
        created = create_run_case_result(result)
        
        assert created.error == "Model invocation failed"
        assert created.classification == "Failed"


class TestGetRunCaseResults:
    """Tests for get_run_case_results."""
    
    def test_get_results_empty(self, aws_setup):
        result = get_run_case_results("run-1")
        
        assert result == []
    
    def test_get_results_multiple(self, aws_setup):
        result1 = RunCaseResult(
            run_id="run-1",
            case_id="case-1",
            classification="Improved",
        )
        result2 = RunCaseResult(
            run_id="run-1",
            case_id="case-2",
            classification="Regressed",
        )
        
        create_run_case_result(result1)
        create_run_case_result(result2)
        
        results = get_run_case_results("run-1")
        
        assert len(results) == 2


class TestDeleteRun:
    """Tests for delete_run."""
    
    def test_delete_run(self, aws_setup):
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            baseline_prompt="Be helpful",
            candidate_prompt="Be concise and helpful",
            rubric="Score on helpfulness and clarity",
        )
        
        create_run(run)
        result = delete_run(run.run_id)
        
        assert result is True
        assert get_run(run.run_id) is None


class TestRunRoutes:
    """Tests for Run route handlers."""
    
    def test_handle_runs_get(self, aws_setup):
        from src.handlers.api.routes.runs import handle_runs
        
        event = {"httpMethod": "GET"}
        result = handle_runs(event)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body == []
    
    def test_handle_runs_post_missing_fields(self, aws_setup):
        from src.handlers.api.routes.runs import handle_runs
        
        event = {
            "httpMethod": "POST",
            "body": json.dumps({}),
        }
        result = handle_runs(event)
        
        assert result["statusCode"] == 400
    
    def test_handle_run_by_id_not_found(self, aws_setup):
        from src.handlers.api.routes.runs import handle_run_by_id
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"runId": "nonexistent"},
        }
        result = handle_run_by_id(event)
        
        assert result["statusCode"] == 404
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/test_runs.py -v
```

Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_runs.py
git commit -m "feat: add tests for Run operations"
```

---

## Verification Checklist

After completing all tasks, verify:

- [ ] All tests pass
- [ ] No mypy errors (if type checking enabled)
- [ ] All API endpoints respond correctly
- [ ] Run execution works with Bedrock (when deployed)
- [ ] Input validation works for all endpoints
- [ ] Error responses are properly formatted
- [ ] CORS headers present on all responses
- [ ] Run status progresses correctly (RUNNING → COMPLETED | PARTIAL | FAILED)
- [ ] Individual case failures don't fail entire run
- [ ] Scores clamped to 1-5 range

## Next Steps

After completing this feature:

1. **Feature 4: Results Display** - Implement results display and comparison
2. Test the API endpoints with curl or Postman
3. Deploy to AWS and verify Bedrock operations
