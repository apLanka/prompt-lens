"""Case route handlers."""

import json
from typing import Any, Dict, Optional

from ..models import Case
from ..dynamodb import get_suite, create_case, get_case, update_case, delete_case

_DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
}


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


def handle_cases(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle /suites/{suiteId}/cases routes."""
    method = event.get("httpMethod")
    suite_id = event.get("pathParameters", {}).get("suiteId")

    if not suite_id:
        return _response(400, json.dumps({"message": "suiteId is required"}))

    suite = get_suite(suite_id)
    if not suite:
        return _response(404, json.dumps({"message": "Suite not found"}))

    if method == "POST":
        return create_case_handler(event, suite_id)
    else:
        return _response(405, json.dumps({"message": "Method not allowed"}))


def handle_case_by_id(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle /suites/{suiteId}/cases/{caseId} routes."""
    method = event.get("httpMethod")
    suite_id = event.get("pathParameters", {}).get("suiteId")
    case_id = event.get("pathParameters", {}).get("caseId")

    if not suite_id or not case_id:
        return _response(
            400, json.dumps({"message": "suiteId and caseId are required"})
        )

    suite = get_suite(suite_id)
    if not suite:
        return _response(404, json.dumps({"message": "Suite not found"}))

    if method == "PATCH":
        return update_case_handler(event, suite_id, case_id)
    elif method == "DELETE":
        return delete_case_handler(suite_id, case_id)
    else:
        return _response(405, json.dumps({"message": "Method not allowed"}))


def create_case_handler(event: Dict[str, Any], suite_id: str) -> Dict[str, Any]:
    """Create a new case in a suite."""
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return _response(400, json.dumps({"message": "Invalid JSON"}))

    input_text = body.get("input")
    if not input_text:
        return _response(400, json.dumps({"message": "input is required"}))

    case = Case(
        suite_id=suite_id,
        input=input_text,
        expected_behavior=body.get("expectedBehavior"),
        tags=body.get("tags", []),
    )

    created = create_case(case)

    return _response(201, json.dumps(created.to_response()))


def update_case_handler(
    event: Dict[str, Any], suite_id: str, case_id: str
) -> Dict[str, Any]:
    """Update a case."""
    existing = get_case(suite_id, case_id)
    if not existing:
        return _response(404, json.dumps({"message": "Case not found"}))

    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return _response(400, json.dumps({"message": "Invalid JSON"}))

    input_text = body.get("input")
    if not input_text:
        return _response(400, json.dumps({"message": "input is required"}))

    updated = update_case(
        suite_id=suite_id,
        case_id=case_id,
        input=input_text,
        expected_behavior=body.get("expectedBehavior"),
        tags=body.get("tags"),
    )

    return _response(200, json.dumps(updated.to_response()))


def delete_case_handler(suite_id: str, case_id: str) -> Dict[str, Any]:
    """Delete a case."""
    existing = get_case(suite_id, case_id)
    if not existing:
        return _response(404, json.dumps({"message": "Case not found"}))

    delete_case(suite_id, case_id)
    return _response(204, "")
