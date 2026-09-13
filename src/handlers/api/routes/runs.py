"""Run route handlers."""

import json
from typing import Any, Dict, Optional

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

_DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
}

MAX_CASES_PER_RUN = 3


def _response(
    status_code: int, body: Any = "", extra_headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    headers = {**_DEFAULT_HEADERS}
    if extra_headers:
        headers.update(extra_headers)
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": body,
    }


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


def get_query_params(event: Dict[str, Any]) -> Dict[str, str]:
    """Extract query string parameters."""
    return event.get("queryStringParameters") or {}


def list_runs_handler(event: Dict[str, Any] = None) -> Dict[str, Any]:
    """List all runs with optional filtering."""
    params = get_query_params(event or {})
    status = params.get("status")
    suite_id = params.get("suiteId")

    runs = list_runs(status=status, suite_id=suite_id)
    return _response(200, json.dumps([r.to_response() for r in runs]))


def create_run_handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """Create and execute a new run."""
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return _response(400, json.dumps({"message": "Invalid JSON"}))

    suite_id = body.get("suiteId")
    model_id = body.get("modelId")
    baseline_prompt = body.get("baselinePrompt")
    candidate_prompt = body.get("candidatePrompt")
    rubric = body.get("rubric")

    if not all([suite_id, model_id, baseline_prompt, candidate_prompt, rubric]):
        return _response(
            400,
            json.dumps(
                {
                    "message": "suiteId, modelId, baselinePrompt, candidatePrompt, and rubric are required"
                }
            ),
        )

    suite = get_suite(suite_id)
    if not suite:
        return _response(404, json.dumps({"message": "Suite not found"}))

    cases = get_cases(suite_id)[:MAX_CASES_PER_RUN]
    if not cases:
        return _response(400, json.dumps({"message": "Suite has no cases"}))

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

    try:
        execute_run(created_run, cases)
        run = get_run(run.run_id)
    except Exception:
        update_run_status(run.run_id, "FAILED")
        run = get_run(run.run_id)

    return _response(201, json.dumps(run.to_response()))


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


def get_run_handler(
    run_id: str, classification: Optional[str] = None
) -> Dict[str, Any]:
    """Get a run with its results."""
    run = get_run(run_id)
    if not run:
        return _response(404, json.dumps({"message": "Run not found"}))

    results = get_run_case_results(run_id, classification=classification)
    response = run.to_response()
    response["results"] = [r.to_response() for r in results]
    response["summary"] = _compute_summary(results)

    return _response(200, json.dumps(response))


def delete_run_handler(run_id: str) -> Dict[str, Any]:
    """Delete a run and all its results."""
    run = get_run(run_id)
    if not run:
        return _response(404, json.dumps({"message": "Run not found"}))

    from ..dynamodb import delete_run

    delete_run(run_id)

    return _response(204, "")


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
            baseline_output, baseline_latency = invoke_model(
                model_id=run.model_id,
                prompt=f"{run.baseline_prompt}\n\n{case.input}",
                temperature=run.temperature,
                max_tokens=run.max_tokens,
            )

            candidate_output, candidate_latency = invoke_model(
                model_id=run.model_id,
                prompt=f"{run.candidate_prompt}\n\n{case.input}",
                temperature=run.temperature,
                max_tokens=run.max_tokens,
            )

            baseline_eval = evaluate_output(
                output=baseline_output,
                rubric=run.rubric,
                model_id=run.model_id,
            )

            candidate_eval = evaluate_output(
                output=candidate_output,
                rubric=run.rubric,
                model_id=run.model_id,
            )

            classification = classify_result(
                baseline_score=baseline_eval["score"],
                candidate_score=candidate_eval["score"],
            )

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
            result = RunCaseResult(
                run_id=run.run_id,
                case_id=case.case_id,
                error=str(e),
                classification="Failed",
            )
            create_run_case_result(result)

    if successful_results == total_cases:
        update_run_status(run.run_id, "COMPLETED")
    elif successful_results > 0:
        update_run_status(run.run_id, "PARTIAL")
    else:
        update_run_status(run.run_id, "FAILED")
