# Results & Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plants to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance run results retrieval with summary statistics, filtering by status and tags, and improved response formats for the frontend to display side-by-side comparisons and classification summaries.

**Architecture:** Extend existing Run handlers with summary computation and filtering capabilities. Add query parameters to list_runs and get_run_case_results for filtering. Compute classification counts server-side for summary cards.

**Tech Stack:** Python 3.11, Lambda, DynamoDB, pytest, moto

**Spec:** `.scratch/wayfinder/FEATURE-BREAKDOWN.md` (Feature 4: Results & Review)

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
- Classification: Improved | Regressed | Unchanged | Needs review | Failed

---

## File Structure

- **Modify:** `src/handlers/api/routes/runs.py` — add summary computation, filtering logic
- **Modify:** `src/handlers/api/dynamodb.py` — add filtered list_runs, filtered get_run_case_results
- **Modify:** `src/handlers/api/models/run.py` — add summary fields to to_response()
- **Modify:** `src/handlers/api/models/run_case_result.py` — add filter matching
- **Create:** `tests/test_results_review.py` — tests for filtering and summary logic
- **Modify:** `tests/test_routes_runs.py` — add tests for filtered endpoints

---

### Task 1: Add Summary Computation to Run Response

**Files:**
- Modify: `src/handlers/api/routes/runs.py:127-137` (get_run_handler)
- Modify: `src/handlers/api/models/run.py:45-61` (to_response)
- Test: `tests/test_results_review.py`

**Interfaces:**
- Consumes: Run, RunCaseResult models, get_run, get_run_case_results
- Produces: Enhanced Run response with summary statistics

- [ ] **Step 1: Write failing test for summary in run response**

```python
# tests/test_results_review.py
"""Tests for Results & Review features."""

import json
import os
import pytest
from moto import mock_aws
import boto3
from src.handlers.api.models import Run, RunCaseResult
from src.handlers.api.dynamodb import (
    create_run,
    create_run_case_result,
    get_run,
)


@pytest.fixture
def aws_setup():
    """Set up AWS mocks."""
    with mock_aws():
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        os.environ["TABLE_NAME"] = "PromptLens"

        conn = boto3.resource("dynamodb", region_name="us-east-1")
        conn.create_table(
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
        yield


class TestRunSummary:
    """Test summary statistics in run response."""

    def test_run_response_includes_summary(self, aws_setup):
        """Run response should include summary counts per classification."""
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="Baseline prompt",
            candidate_prompt="Candidate prompt",
            rubric="Test rubric",
        )
        created_run = create_run(run)

        # Create results with different classifications
        for i, classification in enumerate(["Improved", "Regressed", "Unchanged"]):
            result = RunCaseResult(
                run_id=created_run.run_id,
                case_id=f"case-{i}",
                baseline_output=f"Baseline output {i}",
                candidate_output=f"Candidate output {i}",
                baseline_score=3,
                candidate_score=4 if classification == "Improved" else 2 if classification == "Regressed" else 3,
                baseline_rationale="Baseline rationale",
                candidate_rationale="Candidate rationale",
                baseline_latency_ms=100,
                candidate_latency_ms=120,
                classification=classification,
            )
            create_run_case_result(result)

        # Get run with results
        from src.handlers.api.routes.runs import get_run_handler
        response = get_run_handler(created_run.run_id)
        body = json.loads(response["body"])

        # Verify summary exists
        assert "summary" in body
        assert body["summary"]["total"] == 3
        assert body["summary"]["improved"] == 1
        assert body["summary"]["regressed"] == 1
        assert body["summary"]["unchanged"] == 1
        assert body["summary"]["needsReview"] == 0
        assert body["summary"]["failed"] == 0

    def test_run_response_summary_with_errors(self, aws_setup):
        """Summary should count Failed classifications from errors."""
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="Baseline prompt",
            candidate_prompt="Candidate prompt",
            rubric="Test rubric",
        )
        created_run = create_run(run)

        # Create a failed result
        result = RunCaseResult(
            run_id=created_run.run_id,
            case_id="case-0",
            error="Bedrock invocation failed",
            classification="Failed",
        )
        create_run_case_result(result)

        from src.handlers.api.routes.runs import get_run_handler
        response = get_run_handler(created_run.run_id)
        body = json.loads(response["body"])

        assert body["summary"]["failed"] == 1
        assert body["summary"]["total"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_results_review.py -v`
Expected: FAIL with assertion error (summary not in response)

- [ ] **Step 3: Implement summary computation**

Add to `src/handlers/api/routes/runs.py`:

```python
def _compute_summary(results: list) -> dict:
    """Compute classification summary from results."""
    summary = {
        "total": len(results),
        "improved": 0,
        "regressed": 0,
        "unchanged": 0,
        "needsReview": 0,
        "failed": 0,
    }
    for r in results:
        classification = r.classification if hasattr(r, "classification") else "Failed"
        if classification == "Improved":
            summary["improved"] += 1
        elif classification == "Regressed":
            summary["regressed"] += 1
        elif classification == "Unchanged":
            summary["unchanged"] += 1
        elif classification == "Needs review":
            summary["needsReview"] += 1
        elif classification == "Failed":
            summary["failed"] += 1
    return summary
```

Update `get_run_handler`:

```python
def get_run_handler(run_id: str) -> Dict[str, Any]:
    """Get a run with its results."""
    run = get_run(run_id)
    if not run:
        return _response(404, json.dumps({"message": "Run not found"}))

    results = get_run_case_results(run_id)
    response = run.to_response()
    response["results"] = [r.to_response() for r in results]
    response["summary"] = _compute_summary(results)

    return _response(200, json.dumps(response))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_results_review.py::TestRunSummary -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/handlers/api/routes/runs.py tests/test_results_review.py
git commit -m "feat: add summary statistics to run response"
```

---

### Task 2: Add Filtering to list_runs

**Files:**
- Modify: `src/handlers/api/dynamodb.py:359-382` (list_runs)
- Modify: `src/handlers/api/routes/runs.py:68-71` (list_runs_handler)
- Test: `tests/test_results_review.py`

**Interfaces:**
- Consumes: list_runs with status, suite_id filters
- Produces: Filtered list of runs

- [ ] **Step 1: Write failing test for filtered list_runs**

```python
class TestListRunsFiltering:
    """Test filtering in list_runs."""

    def test_list_runs_filter_by_status(self, aws_setup):
        """Should filter runs by status."""
        # Create runs with different statuses
        for i, status in enumerate(["COMPLETED", "FAILED", "COMPLETED"]):
            run = Run(
                suite_id="suite-1",
                model_id="anthropic.claude-3-sonnet",
                baseline_prompt="Baseline",
                candidate_prompt="Candidate",
                rubric="Rubric",
            )
            run.status = status
            if status in ["COMPLETED", "FAILED"]:
                run.completed_at = "2026-09-13T10:00:00Z"
            create_run(run)

        from src.handlers.api.routes.runs import list_runs_handler
        from unittest.mock import patch

        # Mock the query parameters
        with patch("src.handlers.api.routes.runs.get_query_params", return_value={"status": "COMPLETED"}):
            response = list_runs_handler()
            body = json.loads(response["body"])
            assert len(body) == 2
            assert all(r["status"] == "COMPLETED" for r in body)

    def test_list_runs_filter_by_suite(self, aws_setup):
        """Should filter runs by suite_id."""
        # Create runs for different suites
        for suite_id in ["suite-1", "suite-2", "suite-1"]:
            run = Run(
                suite_id=suite_id,
                model_id="anthropic.claude-3-sonnet",
                baseline_prompt="Baseline",
                candidate_prompt="Candidate",
                rubric="Rubric",
            )
            create_run(run)

        from src.handlers.api.routes.runs import list_runs_handler
        from unittest.mock import patch

        with patch("src.handlers.api.routes.runs.get_query_params", return_value={"suiteId": "suite-1"}):
            response = list_runs_handler()
            body = json.loads(response["body"])
            assert len(body) == 2
            assert all(r["suiteId"] == "suite-1" for r in body)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_results_review.py::TestListRunsFiltering -v`
Expected: FAIL with ImportError (get_query_params not defined)

- [ ] **Step 3: Implement filtering**

Add to `src/handlers/api/routes/runs.py`:

```python
def get_query_params(event: Dict[str, Any]) -> Dict[str, str]:
    """Extract query string parameters."""
    return event.get("queryStringParameters") or {}


def list_runs_handler(event: Dict[str, Any] = None) -> Dict[str, Any]:
    """List all runs with optional filtering."""
    params = get_query_params(event) if event else {}
    status = params.get("status")
    suite_id = params.get("suiteId")

    runs = list_runs(status=status, suite_id=suite_id)
    return _response(200, json.dumps([r.to_response() for r in runs]))
```

Update `dynamodb.py`:

```python
def list_runs(status: Optional[str] = None, suite_id: Optional[str] = None) -> List[Run]:
    """List all runs with optional filtering."""
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

    runs = [
        Run.from_dict(_deserialize_from_dynamodb(item))
        for item in items
        if item.get("PK", "").startswith("RUN#")
    ]

    if status:
        runs = [r for r in runs if r.status == status]
    if suite_id:
        runs = [r for r in runs if r.suite_id == suite_id]

    return runs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_results_review.py::TestListRunsFiltering -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/handlers/api/dynamodb.py src/handlers/api/routes/runs.py tests/test_results_review.py
git commit -m "feat: add status and suite filtering to list_runs"
```

---

### Task 3: Add Filtering to get_run_case_results

**Files:**
- Modify: `src/handlers/api/dynamodb.py:427-446` (get_run_case_results)
- Modify: `src/handlers/api/routes/runs.py:127-137` (get_run_handler)
- Test: `tests/test_results_review.py`

**Interfaces:**
- Consumes: get_run_case_results with classification filter
- Produces: Filtered list of run case results

- [ ] **Step 1: Write failing test for case result filtering**

```python
class TestCaseResultFiltering:
    """Test filtering in get_run_case_results."""

    def test_filter_cases_by_classification(self, aws_setup):
        """Should filter case results by classification."""
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="Baseline",
            candidate_prompt="Candidate",
            rubric="Rubric",
        )
        created_run = create_run(run)

        # Create results with different classifications
        for i, classification in enumerate(["Improved", "Regressed", "Improved"]):
            result = RunCaseResult(
                run_id=created_run.run_id,
                case_id=f"case-{i}",
                baseline_output=f"Output {i}",
                candidate_output=f"Candidate {i}",
                baseline_score=3,
                candidate_score=4 if classification == "Improved" else 2,
                baseline_rationale="Rationale",
                candidate_rationale="Rationale",
                baseline_latency_ms=100,
                candidate_latency_ms=120,
                classification=classification,
            )
            create_run_case_result(result)

        from src.handlers.api.dynamodb import get_run_case_results
        results = get_run_case_results(created_run.run_id, classification="Improved")
        assert len(results) == 2
        assert all(r.classification == "Improved" for r in results)

    def test_filter_cases_by_failed(self, aws_setup):
        """Should return only Failed results when filtering by Failed."""
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="Baseline",
            candidate_prompt="Candidate",
            rubric="Rubric",
        )
        created_run = create_run(run)

        # Create mixed results
        result_ok = RunCaseResult(
            run_id=created_run.run_id,
            case_id="case-0",
            baseline_output="Output",
            candidate_output="Candidate",
            baseline_score=3,
            candidate_score=4,
            baseline_rationale="Rationale",
            candidate_rationale="Rationale",
            baseline_latency_ms=100,
            candidate_latency_ms=120,
            classification="Improved",
        )
        create_run_case_result(result_ok)

        result_failed = RunCaseResult(
            run_id=created_run.run_id,
            case_id="case-1",
            error="Timeout",
            classification="Failed",
        )
        create_run_case_result(result_failed)

        from src.handlers.api.dynamodb import get_run_case_results
        results = get_run_case_results(created_run.run_id, classification="Failed")
        assert len(results) == 1
        assert results[0].classification == "Failed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_results_review.py::TestCaseResultFiltering -v`
Expected: FAIL with TypeError (unexpected keyword argument 'classification')

- [ ] **Step 3: Implement case result filtering**

Update `dynamodb.py`:

```python
def get_run_case_results(run_id: str, classification: Optional[str] = None) -> List[RunCaseResult]:
    """Get all case results for a run with optional classification filter."""
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

    results = [RunCaseResult.from_dict(_deserialize_from_dynamodb(item)) for item in items]

    if classification:
        results = [r for r in results if r.classification == classification]

    return results
```

Update `get_run_handler` to pass classification filter:

```python
def get_run_handler(run_id: str, classification: Optional[str] = None) -> Dict[str, Any]:
    """Get a run with its results."""
    run = get_run(run_id)
    if not run:
        return _response(404, json.dumps({"message": "Run not found"}))

    results = get_run_case_results(run_id, classification=classification)
    response = run.to_response()
    response["results"] = [r.to_response() for r in results]
    response["summary"] = _compute_summary(results)

    return _response(200, json.dumps(response))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_results_review.py::TestCaseResultFiltering -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/handlers/api/dynamodb.py src/handlers/api/routes/runs.py tests/test_results_review.py
git commit -m "feat: add classification filtering to get_run_case_results"
```

---

### Task 4: Update Route Handler to Pass Query Parameters

**Files:**
- Modify: `src/handlers/api/routes/runs.py:40-49` (handle_runs)
- Modify: `src/handlers/api/routes/runs.py:52-65` (handle_run_by_id)
- Test: `tests/test_results_review.py`

**Interfaces:**
- Consumes: event with queryStringParameters
- Produces: Filtered responses

- [ ] **Step 1: Write integration test for filtered endpoints**

```python
class TestFilteredEndpoints:
    """Test filtered API endpoints."""

    def test_get_run_with_classification_filter(self, aws_setup):
        """GET /runs/{runId}?classification=Improved should return only improved results."""
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="Baseline",
            candidate_prompt="Candidate",
            rubric="Rubric",
        )
        created_run = create_run(run)

        # Create mixed results
        for i, classification in enumerate(["Improved", "Regressed"]):
            result = RunCaseResult(
                run_id=created_run.run_id,
                case_id=f"case-{i}",
                baseline_output=f"Output {i}",
                candidate_output=f"Candidate {i}",
                baseline_score=3,
                candidate_score=4 if classification == "Improved" else 2,
                baseline_rationale="Rationale",
                candidate_rationale="Rationale",
                baseline_latency_ms=100,
                candidate_latency_ms=120,
                classification=classification,
            )
            create_run_case_result(result)

        from src.handlers.api.routes.runs import handle_run_by_id
        event = {
            "httpMethod": "GET",
            "pathParameters": {"runId": created_run.run_id},
            "queryStringParameters": {"classification": "Improved"},
        }
        response = handle_run_by_id(event)
        body = json.loads(response["body"])

        assert len(body["results"]) == 1
        assert body["results"][0]["classification"] == "Improved"
        # Summary should reflect filtered results
        assert body["summary"]["improved"] == 1
        assert body["summary"]["regressed"] == 0

    def test_list_runs_with_status_filter(self, aws_setup):
        """GET /runs?status=COMPLETED should return only completed runs."""
        for i, status in enumerate(["COMPLETED", "FAILED"]):
            run = Run(
                suite_id="suite-1",
                model_id="anthropic.claude-3-sonnet",
                baseline_prompt="Baseline",
                candidate_prompt="Candidate",
                rubric="Rubric",
            )
            run.status = status
            if status in ["COMPLETED", "FAILED"]:
                run.completed_at = "2026-09-13T10:00:00Z"
            create_run(run)

        from src.handlers.api.routes.runs import handle_runs
        event = {
            "httpMethod": "GET",
            "queryStringParameters": {"status": "COMPLETED"},
        }
        response = handle_runs(event)
        body = json.loads(response["body"])

        assert len(body) == 1
        assert body[0]["status"] == "COMPLETED"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_results_review.py::TestFilteredEndpoints -v`
Expected: FAIL (event not passed to handler functions)

- [ ] **Step 3: Update route handlers to pass event**

```python
def handle_runs(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle /runs routes."""
    method = event.get("httpMethod")

    if method == "GET":
        return list_runs_handler(event)
    elif method == "POST":
        return create_run_handler(event)
    else:
        return _response(405, json.dumps({"message": "Method not allowed"}))


def handle_run_by_id(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle /runs/{runId} routes."""
    method = event.get("httpMethod")
    run_id = event.get("pathParameters", {}).get("runId")
    classification = (event.get("queryStringParameters") or {}).get("classification")

    if not run_id:
        return _response(400, json.dumps({"message": "runId is required"}))

    if method == "GET":
        return get_run_handler(run_id, classification=classification)
    elif method == "DELETE":
        return delete_run_handler(run_id)
    else:
        return _response(405, json.dumps({"message": "Method not allowed"}))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_results_review.py::TestFilteredEndpoints -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/handlers/api/routes/runs.py tests/test_results_review.py
git commit -m "feat: pass query parameters to route handlers for filtering"
```

---

### Task 5: Add Tag-Based Filtering Support

**Files:**
- Modify: `src/handlers/api/dynamodb.py:427-446` (get_run_case_results)
- Modify: `src/handlers/api/routes/runs.py:127-137` (get_run_handler)
- Modify: `src/handlers/api/models/run_case_result.py` (add tags field)
- Test: `tests/test_results_review.py`

**Interfaces:**
- Consumes: get_run_case_results with tags filter
- Produces: Filtered list of run case results matching any tag

- [ ] **Step 1: Write failing test for tag filtering**

```python
class TestTagFiltering:
    """Test filtering by tags."""

    def test_filter_cases_by_tag(self, aws_setup):
        """Should filter case results by tag."""
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="Baseline",
            candidate_prompt="Candidate",
            rubric="Rubric",
        )
        created_run = create_run(run)

        # Create results with different tags
        result1 = RunCaseResult(
            run_id=created_run.run_id,
            case_id="case-0",
            baseline_output="Output 0",
            candidate_output="Candidate 0",
            baseline_score=3,
            candidate_score=4,
            baseline_rationale="Rationale",
            candidate_rationale="Rationale",
            baseline_latency_ms=100,
            candidate_latency_ms=120,
            classification="Improved",
            tags=["critical", "regression"],
        )
        create_run_case_result(result1)

        result2 = RunCaseResult(
            run_id=created_run.run_id,
            case_id="case-1",
            baseline_output="Output 1",
            candidate_output="Candidate 1",
            baseline_score=3,
            candidate_score=3,
            baseline_rationale="Rationale",
            candidate_rationale="Rationale",
            baseline_latency_ms=100,
            candidate_latency_ms=120,
            classification="Unchanged",
            tags=["performance"],
        )
        create_run_case_result(result2)

        from src.handlers.api.dynamodb import get_run_case_results
        results = get_run_case_results(created_run.run_id, tags=["critical"])
        assert len(results) == 1
        assert results[0].case_id == "case-0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_results_review.py::TestTagFiltering -v`
Expected: FAIL with TypeError (unexpected keyword argument 'tags')

- [ ] **Step 3: Add tags field to RunCaseResult**

Update `src/handlers/api/models/run_case_result.py`:

```python
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
    baseline_latency_ms: Optional[int] = None
    candidate_latency_ms: Optional[int] = None
    classification: str = "Needs review"
    error: Optional[str] = None
    tags: Optional[List[str]] = None

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
        if self.tags is not None:
            result["tags"] = self.tags
        return result

    def to_response(self) -> dict:
        """Convert to API response format."""
        result = {
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
        if self.tags is not None:
            result["tags"] = self.tags
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "RunCaseResult":
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
            tags=data.get("tags"),
        )
```

- [ ] **Step 4: Implement tag filtering in dynamodb.py**

```python
def get_run_case_results(
    run_id: str,
    classification: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> List[RunCaseResult]:
    """Get all case results for a run with optional filters."""
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

    results = [RunCaseResult.from_dict(_deserialize_from_dynamodb(item)) for item in items]

    if classification:
        results = [r for r in results if r.classification == classification]

    if tags:
        results = [r for r in results if r.tags and any(t in r.tags for t in tags)]

    return results
```

- [ ] **Step 5: Update route handler to pass tags filter**

Update `get_run_handler`:

```python
def get_run_handler(
    run_id: str,
    classification: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Get a run with its results."""
    run = get_run(run_id)
    if not run:
        return _response(404, json.dumps({"message": "Run not found"}))

    results = get_run_case_results(run_id, classification=classification, tags=tags)
    response = run.to_response()
    response["results"] = [r.to_response() for r in results]
    response["summary"] = _compute_summary(results)

    return _response(200, json.dumps(response))
```

Update `handle_run_by_id`:

```python
def handle_run_by_id(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle /runs/{runId} routes."""
    method = event.get("httpMethod")
    run_id = event.get("pathParameters", {}).get("runId")
    params = event.get("queryStringParameters") or {}
    classification = params.get("classification")
    tags = params.get("tags", "").split(",") if params.get("tags") else None

    if not run_id:
        return _response(400, json.dumps({"message": "runId is required"}))

    if method == "GET":
        return get_run_handler(run_id, classification=classification, tags=tags)
    elif method == "DELETE":
        return delete_run_handler(run_id)
    else:
        return _response(405, json.dumps({"message": "Method not allowed"}))
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_results_review.py::TestTagFiltering -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/handlers/api/models/run_case_result.py src/handlers/api/dynamodb.py src/handlers/api/routes/runs.py tests/test_results_review.py
git commit -m "feat: add tag-based filtering to case results"
```

---

### Task 6: Final Verification and Cleanup

**Files:**
- All modified files
- Test: Full test suite

**Interfaces:**
- All existing interfaces preserved
- No breaking changes

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass (existing + new)

- [ ] **Step 2: Verify SAM template**

Run: `./sam validate --lint`
Expected: Template is valid

- [ ] **Step 3: Final commit with any cleanup**

```bash
git add -A
git commit -m "feat: complete Results & Review feature"
```

---

## Summary

**Features Added:**
1. Summary statistics (counts per classification) in GET /runs/{runId} response
2. Filtering runs by status (GET /runs?status=COMPLETED)
3. Filtering runs by suite (GET /runs?suiteId=xxx)
4. Filtering case results by classification (GET /runs/{runId}?classification=Improved)
5. Filtering case results by tags (GET /runs/{runId}?tags=critical,regression)

**API Changes:**
- `GET /runs?status=X&suiteId=Y` — filtered list
- `GET /runs/{runId}?classification=X&tags=Y,Z` — filtered results with summary
- Response includes `summary` object with counts: `{total, improved, regressed, unchanged, needsReview, failed}`
- Case results include optional `tags` field

**Backward Compatible:**
- All existing endpoints continue to work
- New fields are optional in responses
- Filters are optional query parameters
