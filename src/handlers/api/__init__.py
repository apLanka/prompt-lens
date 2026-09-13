"""PromptLens API Lambda Handler."""

import json
import os
from typing import Any, Dict


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for API requests.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    table_name = os.environ.get("TABLE_NAME", "PromptLens")

    # Health check endpoint
    if event.get("path") == "/health":
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "status": "healthy",
                    "table": table_name,
                }
            ),
        }

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
