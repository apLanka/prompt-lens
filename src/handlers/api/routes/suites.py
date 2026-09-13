"""Suite route handlers."""

import json
from typing import Any, Dict, Optional

from ..models import Suite
from ..dynamodb import (
    create_suite,
    get_suite,
    list_suites,
    update_suite,
    delete_suite,
    get_cases,
)

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


def handle_suites(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle /suites routes."""
    method = event.get("httpMethod")

    if method == "GET":
        return list_suites_handler()
    elif method == "POST":
        return create_suite_handler(event)
    else:
        return _response(405, json.dumps({"message": "Method not allowed"}))


def handle_suite_by_id(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle /suites/{suiteId} routes."""
    method = event.get("httpMethod")
    suite_id = event.get("pathParameters", {}).get("suiteId")

    if not suite_id:
        return _response(400, json.dumps({"message": "suiteId is required"}))

    if method == "GET":
        return get_suite_handler(suite_id)
    elif method == "PATCH":
        return update_suite_handler(event, suite_id)
    elif method == "DELETE":
        return delete_suite_handler(suite_id)
    else:
        return _response(405, json.dumps({"message": "Method not allowed"}))


def list_suites_handler() -> Dict[str, Any]:
    """List all suites."""
    suites = list_suites()
    return _response(200, json.dumps([s.to_response() for s in suites]))


def create_suite_handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new suite."""
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return _response(400, json.dumps({"message": "Invalid JSON"}))

    name = body.get("name")
    if not name:
        return _response(400, json.dumps({"message": "name is required"}))

    suite = Suite(name=name)
    created = create_suite(suite)

    return _response(201, json.dumps(created.to_response()))


def get_suite_handler(suite_id: str) -> Dict[str, Any]:
    """Get a suite with its cases."""
    suite = get_suite(suite_id)
    if not suite:
        return _response(404, json.dumps({"message": "Suite not found"}))

    cases = get_cases(suite_id)
    response = suite.to_response()
    response["cases"] = [c.to_response() for c in cases]

    return _response(200, json.dumps(response))


def update_suite_handler(event: Dict[str, Any], suite_id: str) -> Dict[str, Any]:
    """Update a suite's name."""
    suite = get_suite(suite_id)
    if not suite:
        return _response(404, json.dumps({"message": "Suite not found"}))

    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return _response(400, json.dumps({"message": "Invalid JSON"}))

    name = body.get("name")
    if not name:
        return _response(400, json.dumps({"message": "name is required"}))

    updated = update_suite(suite_id, name)
    return _response(200, json.dumps(updated.to_response()))


def delete_suite_handler(suite_id: str) -> Dict[str, Any]:
    """Delete a suite and all its cases."""
    suite = get_suite(suite_id)
    if not suite:
        return _response(404, json.dumps({"message": "Suite not found"}))

    delete_suite(suite_id)
    return _response(204, "")
