"""Tests for Case route handlers."""

import json
import os
import pytest
import boto3
from moto import mock_aws

from src.handlers.api.models import Suite, Case
from src.handlers.api import dynamodb
from src.handlers.api.routes.cases import (
    handle_cases,
    handle_case_by_id,
)


@pytest.fixture
def aws_setup():
    """Set up mock AWS environment."""
    with mock_aws():
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        os.environ["TABLE_NAME"] = "PromptLens"

        dynamodb_resource = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb_resource.create_table(
            TableName="PromptLens",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "SK-index",
                    "KeySchema": [
                        {"AttributeName": "SK", "KeyType": "HASH"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield


def make_event(method, path_params=None, body=None):
    """Helper to create API Gateway event."""
    event = {
        "httpMethod": method,
        "pathParameters": path_params or {},
    }
    if body is not None:
        event["body"] = json.dumps(body) if isinstance(body, dict) else body
    return event


class TestHandleCases:
    def test_post_create_case(self, aws_setup):
        suite = Suite(name="Test Suite")
        dynamodb.create_suite(suite)

        event = make_event(
            "POST",
            path_params={"suiteId": suite.suite_id},
            body={"input": "What is 2+2?"},
        )
        response = handle_cases(event)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["input"] == "What is 2+2?"
        assert body["suiteId"] == suite.suite_id
        assert "caseId" in body

    def test_post_create_case_with_optional_fields(self, aws_setup):
        suite = Suite(name="Test Suite")
        dynamodb.create_suite(suite)

        event = make_event(
            "POST",
            path_params={"suiteId": suite.suite_id},
            body={
                "input": "test",
                "expectedBehavior": "Should return 4",
                "tags": ["math"],
            },
        )
        response = handle_cases(event)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["expectedBehavior"] == "Should return 4"
        assert body["tags"] == ["math"]

    def test_post_create_case_missing_input(self, aws_setup):
        suite = Suite(name="Test Suite")
        dynamodb.create_suite(suite)

        event = make_event(
            "POST",
            path_params={"suiteId": suite.suite_id},
            body={},
        )
        response = handle_cases(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["message"] == "input is required"

    def test_post_create_case_invalid_json(self, aws_setup):
        suite = Suite(name="Test Suite")
        dynamodb.create_suite(suite)

        event = make_event(
            "POST",
            path_params={"suiteId": suite.suite_id},
            body="not json",
        )
        response = handle_cases(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["message"] == "Invalid JSON"

    def test_post_create_case_suite_not_found(self, aws_setup):
        event = make_event(
            "POST",
            path_params={"suiteId": "nonexistent"},
            body={"input": "test"},
        )
        response = handle_cases(event)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["message"] == "Suite not found"

    def test_post_create_case_missing_suite_id(self, aws_setup):
        event = make_event("POST", path_params={}, body={"input": "test"})
        response = handle_cases(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["message"] == "suiteId is required"

    def test_method_not_allowed(self, aws_setup):
        suite = Suite(name="Test Suite")
        dynamodb.create_suite(suite)

        event = make_event("GET", path_params={"suiteId": suite.suite_id})
        response = handle_cases(event)

        assert response["statusCode"] == 405


class TestHandleCaseById:
    def test_patch_update_case(self, aws_setup):
        suite = Suite(name="Test Suite")
        dynamodb.create_suite(suite)
        case = Case(suite_id=suite.suite_id, input="old input")
        dynamodb.create_case(case)

        event = make_event(
            "PATCH",
            path_params={"suiteId": suite.suite_id, "caseId": case.case_id},
            body={"input": "new input"},
        )
        response = handle_case_by_id(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["input"] == "new input"

    def test_patch_update_case_with_optional_fields(self, aws_setup):
        suite = Suite(name="Test Suite")
        dynamodb.create_suite(suite)
        case = Case(suite_id=suite.suite_id, input="test")
        dynamodb.create_case(case)

        event = make_event(
            "PATCH",
            path_params={"suiteId": suite.suite_id, "caseId": case.case_id},
            body={
                "input": "updated",
                "expectedBehavior": "new behavior",
                "tags": ["updated"],
            },
        )
        response = handle_case_by_id(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["input"] == "updated"
        assert body["expectedBehavior"] == "new behavior"
        assert body["tags"] == ["updated"]

    def test_patch_update_case_not_found(self, aws_setup):
        suite = Suite(name="Test Suite")
        dynamodb.create_suite(suite)

        event = make_event(
            "PATCH",
            path_params={"suiteId": suite.suite_id, "caseId": "nonexistent"},
            body={"input": "test"},
        )
        response = handle_case_by_id(event)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["message"] == "Case not found"

    def test_patch_update_case_missing_input(self, aws_setup):
        suite = Suite(name="Test Suite")
        dynamodb.create_suite(suite)
        case = Case(suite_id=suite.suite_id, input="test")
        dynamodb.create_case(case)

        event = make_event(
            "PATCH",
            path_params={"suiteId": suite.suite_id, "caseId": case.case_id},
            body={},
        )
        response = handle_case_by_id(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["message"] == "input is required"

    def test_delete_case(self, aws_setup):
        suite = Suite(name="Test Suite")
        dynamodb.create_suite(suite)
        case = Case(suite_id=suite.suite_id, input="to delete")
        dynamodb.create_case(case)

        event = make_event(
            "DELETE",
            path_params={"suiteId": suite.suite_id, "caseId": case.case_id},
        )
        response = handle_case_by_id(event)

        assert response["statusCode"] == 204
        assert dynamodb.get_case(suite.suite_id, case.case_id) is None

    def test_delete_case_not_found(self, aws_setup):
        suite = Suite(name="Test Suite")
        dynamodb.create_suite(suite)

        event = make_event(
            "DELETE",
            path_params={"suiteId": suite.suite_id, "caseId": "nonexistent"},
        )
        response = handle_case_by_id(event)

        assert response["statusCode"] == 404

    def test_delete_case_suite_not_found(self, aws_setup):
        event = make_event(
            "DELETE",
            path_params={"suiteId": "nonexistent", "caseId": "some-case"},
        )
        response = handle_case_by_id(event)

        assert response["statusCode"] == 404

    def test_missing_params(self, aws_setup):
        event = make_event("PATCH", path_params={})
        response = handle_case_by_id(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["message"] == "suiteId and caseId are required"

    def test_method_not_allowed(self, aws_setup):
        suite = Suite(name="Test Suite")
        dynamodb.create_suite(suite)
        case = Case(suite_id=suite.suite_id, input="test")
        dynamodb.create_case(case)

        event = make_event(
            "GET",
            path_params={"suiteId": suite.suite_id, "caseId": case.case_id},
        )
        response = handle_case_by_id(event)

        assert response["statusCode"] == 405
