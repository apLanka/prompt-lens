"""DynamoDB operations for Suite, Case, Run, and RunCaseResult management."""

import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
import boto3
from boto3.dynamodb.conditions import Key

from .models import Suite, Case, Run, RunCaseResult


def _sanitize_for_dynamodb(item: dict) -> dict:
    """Convert float values to Decimal for DynamoDB compatibility."""
    result = {}
    for k, v in item.items():
        if isinstance(v, float):
            result[k] = Decimal(str(v))
        elif isinstance(v, dict):
            result[k] = _sanitize_for_dynamodb(v)
        elif isinstance(v, list):
            result[k] = [
                _sanitize_for_dynamodb(i)
                if isinstance(i, dict)
                else Decimal(str(i))
                if isinstance(i, float)
                else i
                for i in v
            ]
        else:
            result[k] = v
    return result


def _deserialize_from_dynamodb(item: dict) -> dict:
    """Convert Decimal values back to native Python types."""
    result = {}
    for k, v in item.items():
        if isinstance(v, Decimal):
            if v == int(v):
                result[k] = int(v)
            else:
                result[k] = float(v)
        elif isinstance(v, dict):
            result[k] = _deserialize_from_dynamodb(v)
        elif isinstance(v, list):
            result[k] = [
                _deserialize_from_dynamodb(i)
                if isinstance(i, dict)
                else int(i)
                if isinstance(i, Decimal) and i == int(i)
                else float(i)
                if isinstance(i, Decimal)
                else i
                for i in v
            ]
        else:
            result[k] = v
    return result


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
        Suite(
            suite_id=item["suite_id"],
            name=item["name"],
            created_at=item["created_at"],
            updated_at=item["updated_at"],
        )
        for item in items
    ]


def update_suite(suite_id: str, name: str) -> Optional[Suite]:
    """Update suite name."""
    table = get_table()

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

    if case.expected_behavior is not None:
        item["expected_behavior"] = case.expected_behavior

    if case.tags is not None:
        item["tags"] = case.tags

    table.put_item(Item=item)

    return case


def get_cases(suite_id: str) -> List[Case]:
    """Get all cases for a suite."""
    table = get_table()

    items: List[dict] = []
    response = table.query(
        KeyConditionExpression=Key("PK").eq(f"SUITE#{suite_id}")
        & Key("SK").begins_with("CASE#"),
    )
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=Key("PK").eq(f"SUITE#{suite_id}")
            & Key("SK").begins_with("CASE#"),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    return [
        Case(
            case_id=item["case_id"],
            suite_id=item["suite_id"],
            input=item["input"],
            expected_behavior=item.get("expected_behavior"),
            tags=item.get("tags", []),
        )
        for item in items
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


def create_run(run: Run) -> Run:
    """Create a new run in DynamoDB."""
    table = get_table()

    item = {
        "PK": f"RUN#{run.run_id}",
        "SK": "META",
        **run.to_dict(),
    }

    table.put_item(Item=_sanitize_for_dynamodb(item))

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

    return Run.from_dict(_deserialize_from_dynamodb(item))


def list_runs(
    status: Optional[str] = None, suite_id: Optional[str] = None
) -> List[Run]:
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
    return Run.from_dict(_deserialize_from_dynamodb(attributes))


def create_run_case_result(result: RunCaseResult) -> RunCaseResult:
    """Create a new run-case result in DynamoDB."""
    table = get_table()

    item = {
        "PK": f"RUN#{result.run_id}",
        "SK": f"CASE#{result.case_id}",
        **result.to_dict(),
    }

    table.put_item(Item=_sanitize_for_dynamodb(item))

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

    return [RunCaseResult.from_dict(_deserialize_from_dynamodb(item)) for item in items]


def delete_run(run_id: str) -> bool:
    """Delete run and all its case results."""
    table = get_table()

    items: List[dict] = []
    response = table.query(
        KeyConditionExpression=Key("PK").eq(f"RUN#{run_id}"),
    )
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=Key("PK").eq(f"RUN#{run_id}"),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(
                Key={
                    "PK": item["PK"],
                    "SK": item["SK"],
                }
            )

    return True
