"""Suite route handlers."""

import json
from typing import Any, Dict

from ..models import Suite
from ..dynamodb import (
    create_suite,
    get_suite,
    list_suites,
    update_suite,
    delete_suite,
    get_cases,
)


def handle_suites(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle /suites routes."""
    method = event.get("httpMethod")

    if method == "GET":
        return list_suites_handler()
    elif method == "POST":
        return create_suite_handler(event)
    else:
        return {
            "statusCode": 405,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "Method not allowed"}),
        }


def handle_suite_by_id(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle /suites/{suiteId} routes."""
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

    if method == "GET":
        return get_suite_handler(suite_id)
    elif method == "PATCH":
        return update_suite_handler(event, suite_id)
    elif method == "DELETE":
        return delete_suite_handler(suite_id)
    else:
        return {
            "statusCode": 405,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "Method not allowed"}),
        }


def list_suites_handler() -> Dict[str, Any]:
    """List all suites."""
    suites = list_suites()
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps([s.to_response() for s in suites]),
    }


def create_suite_handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new suite."""
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

    name = body.get("name")
    if not name:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "name is required"}),
        }

    suite = Suite(name=name)
    created = create_suite(suite)

    return {
        "statusCode": 201,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(created.to_response()),
    }


def get_suite_handler(suite_id: str) -> Dict[str, Any]:
    """Get a suite with its cases."""
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

    cases = get_cases(suite_id)
    response = suite.to_response()
    response["cases"] = [c.to_response() for c in cases]

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(response),
    }


def update_suite_handler(event: Dict[str, Any], suite_id: str) -> Dict[str, Any]:
    """Update a suite's name."""
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

    name = body.get("name")
    if not name:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "name is required"}),
        }

    updated = update_suite(suite_id, name)
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(updated.to_response()),
    }


def delete_suite_handler(suite_id: str) -> Dict[str, Any]:
    """Delete a suite and all its cases."""
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

    delete_suite(suite_id)
    return {
        "statusCode": 204,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": "",
    }
