"""DynamoDB operations for Suite and Case management."""

import os
from typing import List, Optional
import boto3
from boto3.dynamodb.conditions import Key

from .models import Suite, Case


def get_table():
    """Get DynamoDB table resource."""
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(os.environ.get("TABLE_NAME", "PromptLens"))


def create_suite(suite: Suite) -> Suite:
    """Create a new suite in DynamoDB."""
    table = get_table()

    # Create suite metadata
    table.put_item(
        Item={
            "PK": f"SUITE#{suite.suite_id}",
            "SK": "META",
            "suite_id": suite.suite_id,
            "name": suite.name,
            "created_at": suite.created_at,
            "updated_at": suite.updated_at,
        }
    )

    return suite


def get_suite(suite_id: str) -> Optional[Suite]:
    """Get a suite by ID."""
    table = get_table()

    response = table.get_item(
        Key={
            "PK": f"SUITE#{suite_id}",
            "SK": "META",
        }
    )

    item = response.get("Item")
    if not item:
        return None

    return Suite(
        suite_id=item["suite_id"],
        name=item["name"],
        created_at=item["created_at"],
        updated_at=item["updated_at"],
    )


def list_suites() -> List[Suite]:
    """List all suites."""
    table = get_table()

    response = table.query(
        IndexName="SK-index",
        KeyConditionExpression=Key("SK").eq("META"),
    )

    return [
        Suite(
            suite_id=item["suite_id"],
            name=item["name"],
            created_at=item["created_at"],
            updated_at=item["updated_at"],
        )
        for item in response.get("Items", [])
    ]


def update_suite(suite_id: str, name: str) -> Optional[Suite]:
    """Update suite name."""
    table = get_table()

    from datetime import datetime, timezone

    updated_at = datetime.now(timezone.utc).isoformat()

    response = table.update_item(
        Key={
            "PK": f"SUITE#{suite_id}",
            "SK": "META",
        },
        UpdateExpression="SET #name = :name, updated_at = :updated_at",
        ExpressionAttributeNames={"#name": "name"},
        ExpressionAttributeValues={
            ":name": name,
            ":updated_at": updated_at,
        },
        ReturnValues="ALL_NEW",
    )

    attributes = response.get("Attributes", {})
    return Suite(
        suite_id=attributes["suite_id"],
        name=attributes["name"],
        created_at=attributes["created_at"],
        updated_at=attributes["updated_at"],
    )


def delete_suite(suite_id: str) -> bool:
    """Delete suite and all its cases."""
    table = get_table()

    # First, get all cases in the suite
    response = table.query(
        KeyConditionExpression=Key("PK").eq(f"SUITE#{suite_id}"),
    )

    # Delete suite metadata and all cases
    with table.batch_writer() as batch:
        for item in response.get("Items", []):
            batch.delete_item(
                Key={
                    "PK": item["PK"],
                    "SK": item["SK"],
                }
            )

    return True


def create_case(case: Case) -> Case:
    """Create a new case in a suite."""
    table = get_table()

    item = {
        "PK": f"SUITE#{case.suite_id}",
        "SK": f"CASE#{case.case_id}",
        "case_id": case.case_id,
        "suite_id": case.suite_id,
        "input": case.input,
    }

    if case.expected_behavior:
        item["expected_behavior"] = case.expected_behavior

    if case.tags:
        item["tags"] = case.tags

    table.put_item(Item=item)

    return case


def get_cases(suite_id: str) -> List[Case]:
    """Get all cases for a suite."""
    table = get_table()

    response = table.query(
        KeyConditionExpression=Key("PK").eq(f"SUITE#{suite_id}")
        & Key("SK").begins_with("CASE#"),
    )

    return [
        Case(
            case_id=item["case_id"],
            suite_id=item["suite_id"],
            input=item["input"],
            expected_behavior=item.get("expected_behavior"),
            tags=item.get("tags", []),
        )
        for item in response.get("Items", [])
    ]


def get_case(suite_id: str, case_id: str) -> Optional[Case]:
    """Get a specific case."""
    table = get_table()

    response = table.get_item(
        Key={
            "PK": f"SUITE#{suite_id}",
            "SK": f"CASE#{case_id}",
        }
    )

    item = response.get("Item")
    if not item:
        return None

    return Case(
        case_id=item["case_id"],
        suite_id=item["suite_id"],
        input=item["input"],
        expected_behavior=item.get("expected_behavior"),
        tags=item.get("tags", []),
    )


def update_case(
    suite_id: str,
    case_id: str,
    input: str,
    expected_behavior: str = None,
    tags: List[str] = None,
) -> Optional[Case]:
    """Update a case."""
    table = get_table()

    update_expr = "SET #input = :input"
    expr_names = {"#input": "input"}
    expr_values = {":input": input}

    if expected_behavior is not None:
        update_expr += ", expected_behavior = :expected_behavior"
        expr_values[":expected_behavior"] = expected_behavior

    if tags is not None:
        update_expr += ", tags = :tags"
        expr_values[":tags"] = tags

    response = table.update_item(
        Key={
            "PK": f"SUITE#{suite_id}",
            "SK": f"CASE#{case_id}",
        },
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
        ReturnValues="ALL_NEW",
    )

    attributes = response.get("Attributes", {})
    return Case(
        case_id=attributes["case_id"],
        suite_id=attributes["suite_id"],
        input=attributes["input"],
        expected_behavior=attributes.get("expected_behavior"),
        tags=attributes.get("tags", []),
    )


def delete_case(suite_id: str, case_id: str) -> bool:
    """Delete a case."""
    table = get_table()

    table.delete_item(
        Key={
            "PK": f"SUITE#{suite_id}",
            "SK": f"CASE#{case_id}",
        }
    )

    return True
