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
