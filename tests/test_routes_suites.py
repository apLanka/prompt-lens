"""Tests for Suite route handlers."""

import json
import os
import pytest
import boto3
from moto import mock_aws

from src.handlers.api.models import Suite, Case
from src.handlers.api import dynamodb
from src.handlers.api.routes.suites import (
    handle_suites,
    handle_suite_by_id,
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


def make_event(method, path=None, path_params=None, body=None):
    """Helper to create API Gateway event."""
    event = {
        "httpMethod": method,
        "pathParameters": path_params or {},
    }
    if body is not None:
        event["body"] = json.dumps(body) if isinstance(body, dict) else body
    return event


class TestHandleSuites:
    def test_get_list_suites_empty(self, aws_setup):
        event = make_event("GET")
        response = handle_suites(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body == []

    def test_get_list_suites(self, aws_setup):
        dynamodb.create_suite(Suite(name="Suite 1"))
        dynamodb.create_suite(Suite(name="Suite 2"))

        event = make_event("GET")
        response = handle_suites(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body) == 2

    def test_post_create_suite(self, aws_setup):
        event = make_event("POST", body={"name": "New Suite"})
        response = handle_suites(event)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["name"] == "New Suite"
        assert "suiteId" in body

    def test_post_create_suite_missing_name(self, aws_setup):
        event = make_event("POST", body={})
        response = handle_suites(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["message"] == "name is required"

    def test_post_create_suite_invalid_json(self, aws_setup):
        event = make_event("POST", body="not json")
        response = handle_suites(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["message"] == "Invalid JSON"

    def test_method_not_allowed(self, aws_setup):
        event = make_event("DELETE")
        response = handle_suites(event)

        assert response["statusCode"] == 405
        body = json.loads(response["body"])
        assert body["message"] == "Method not allowed"


class TestHandleSuiteById:
    def test_get_suite_found(self, aws_setup):
        suite = Suite(name="Test Suite")
        dynamodb.create_suite(suite)

        event = make_event("GET", path_params={"suiteId": suite.suite_id})
        response = handle_suite_by_id(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["name"] == "Test Suite"
        assert body["suiteId"] == suite.suite_id
        assert "cases" in body

    def test_get_suite_not_found(self, aws_setup):
        event = make_event("GET", path_params={"suiteId": "nonexistent"})
        response = handle_suite_by_id(event)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["message"] == "Suite not found"

    def test_get_suite_missing_id(self, aws_setup):
        event = make_event("GET", path_params={})
        response = handle_suite_by_id(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["message"] == "suiteId is required"

    def test_patch_update_suite(self, aws_setup):
        suite = Suite(name="Old Name")
        dynamodb.create_suite(suite)

        event = make_event(
            "PATCH",
            path_params={"suiteId": suite.suite_id},
            body={"name": "New Name"},
        )
        response = handle_suite_by_id(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["name"] == "New Name"

    def test_patch_update_suite_missing_name(self, aws_setup):
        suite = Suite(name="Test")
        dynamodb.create_suite(suite)

        event = make_event(
            "PATCH",
            path_params={"suiteId": suite.suite_id},
            body={},
        )
        response = handle_suite_by_id(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["message"] == "name is required"

    def test_delete_suite(self, aws_setup):
        suite = Suite(name="To Delete")
        dynamodb.create_suite(suite)

        event = make_event("DELETE", path_params={"suiteId": suite.suite_id})
        response = handle_suite_by_id(event)

        assert response["statusCode"] == 204

        # Verify deleted
        assert dynamodb.get_suite(suite.suite_id) is None

    def test_delete_suite_not_found(self, aws_setup):
        event = make_event("DELETE", path_params={"suiteId": "nonexistent"})
        response = handle_suite_by_id(event)

        assert response["statusCode"] == 404

    def test_method_not_allowed(self, aws_setup):
        event = make_event("POST", path_params={"suiteId": "some-id"})
        response = handle_suite_by_id(event)

        assert response["statusCode"] == 405
