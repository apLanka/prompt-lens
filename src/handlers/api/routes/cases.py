"""Case route handlers."""

import json
from typing import Any, Dict

from ..models import Case
from ..dynamodb import get_suite, create_case, get_case, update_case, delete_case


def handle_cases(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle /suites/{suiteId}/cases routes."""
    method = event.get("httpMethod")
    suite_id = event.get("pathParameters", {}).get("suiteId")

    if not suite_id:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "suiteId is required"}),
        }

    # Verify suite exists
    suite = get_suite(suite_id)
    if not suite:
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "Suite not found"}),
        }

    if method == "POST":
        return create_case_handler(event, suite_id)
    else:
        return {
            "statusCode": 405,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "Method not allowed"}),
        }


def handle_case_by_id(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle /suites/{suiteId}/cases/{caseId} routes."""
    method = event.get("httpMethod")
    suite_id = event.get("pathParameters", {}).get("suiteId")
    case_id = event.get("pathParameters", {}).get("caseId")

    if not suite_id or not case_id:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "suiteId and caseId are required"}),
        }

    # Verify suite exists
    suite = get_suite(suite_id)
    if not suite:
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "Suite not found"}),
        }

    if method == "PATCH":
        return update_case_handler(event, suite_id, case_id)
    elif method == "DELETE":
        return delete_case_handler(suite_id, case_id)
    else:
        return {
            "statusCode": 405,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "Method not allowed"}),
        }


def create_case_handler(event: Dict[str, Any], suite_id: str) -> Dict[str, Any]:
    """Create a new case in a suite."""
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "Invalid JSON"}),
        }

    input_text = body.get("input")
    if not input_text:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "input is required"}),
        }

    case = Case(
        suite_id=suite_id,
        input=input_text,
        expected_behavior=body.get("expectedBehavior"),
        tags=body.get("tags", []),
    )

    created = create_case(case)

    return {
        "statusCode": 201,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(created.to_response()),
    }


def update_case_handler(
    event: Dict[str, Any], suite_id: str, case_id: str
) -> Dict[str, Any]:
    """Update a case."""
    existing = get_case(suite_id, case_id)
    if not existing:
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "Case not found"}),
        }

    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "Invalid JSON"}),
        }

    input_text = body.get("input")
    if not input_text:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "input is required"}),
        }

    updated = update_case(
        suite_id=suite_id,
        case_id=case_id,
        input=input_text,
        expected_behavior=body.get("expectedBehavior"),
        tags=body.get("tags"),
    )

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(updated.to_response()),
    }


def delete_case_handler(suite_id: str, case_id: str) -> Dict[str, Any]:
    """Delete a case."""
    existing = get_case(suite_id, case_id)
    if not existing:
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "Case not found"}),
        }

    delete_case(suite_id, case_id)
    return {
        "statusCode": 204,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": "",
    }
