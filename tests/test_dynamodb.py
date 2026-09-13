"""Tests for DynamoDB operations module."""

import os
import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch

from src.handlers.api.models import Suite, Case
from src.handlers.api import dynamodb


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

        # Create the table with GSI for list_suites
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


class TestCreateSuite:
    def test_create_suite(self, aws_setup):
        suite = Suite(name="Test Suite")
        result = dynamodb.create_suite(suite)

        assert result.suite_id == suite.suite_id
        assert result.name == "Test Suite"

    def test_create_suite_verifies_dynamodb_item(self, aws_setup):
        suite = Suite(name="My Suite")
        dynamodb.create_suite(suite)

        table = dynamodb.get_table()
        response = table.get_item(Key={"PK": f"SUITE#{suite.suite_id}", "SK": "META"})
        item = response["Item"]
        assert item["name"] == "My Suite"
        assert item["suite_id"] == suite.suite_id


class TestGetSuite:
    def test_get_existing_suite(self, aws_setup):
        suite = Suite(name="Existing Suite")
        dynamodb.create_suite(suite)

        result = dynamodb.get_suite(suite.suite_id)
        assert result is not None
        assert result.name == "Existing Suite"
        assert result.suite_id == suite.suite_id

    def test_get_nonexistent_suite(self, aws_setup):
        result = dynamodb.get_suite("nonexistent-id")
        assert result is None


class TestListSuites:
    def test_list_empty(self, aws_setup):
        result = dynamodb.list_suites()
        assert result == []

    def test_list_multiple_suites(self, aws_setup):
        suite1 = Suite(name="Suite 1")
        suite2 = Suite(name="Suite 2")
        dynamodb.create_suite(suite1)
        dynamodb.create_suite(suite2)

        result = dynamodb.list_suites()
        assert len(result) == 2
        names = {s.name for s in result}
        assert names == {"Suite 1", "Suite 2"}


class TestUpdateSuite:
    def test_update_suite_name(self, aws_setup):
        suite = Suite(name="Old Name")
        dynamodb.create_suite(suite)

        result = dynamodb.update_suite(suite.suite_id, "New Name")
        assert result.name == "New Name"
        assert result.suite_id == suite.suite_id

    def test_update_suite_updates_timestamp(self, aws_setup):
        suite = Suite(name="Test")
        dynamodb.create_suite(suite)
        original_updated = suite.updated_at

        result = dynamodb.update_suite(suite.suite_id, "Test Updated")
        assert result.updated_at != original_updated


class TestDeleteSuite:
    def test_delete_suite(self, aws_setup):
        suite = Suite(name="To Delete")
        dynamodb.create_suite(suite)

        result = dynamodb.delete_suite(suite.suite_id)
        assert result is True

        # Verify suite is gone
        retrieved = dynamodb.get_suite(suite.suite_id)
        assert retrieved is None

    def test_delete_suite_with_cases(self, aws_setup):
        suite = Suite(name="With Cases")
        dynamodb.create_suite(suite)

        case = Case(suite_id=suite.suite_id, input="test input")
        dynamodb.create_case(case)

        # Verify case exists
        cases = dynamodb.get_cases(suite.suite_id)
        assert len(cases) == 1

        # Delete suite
        dynamodb.delete_suite(suite.suite_id)

        # Verify both suite and cases are gone
        assert dynamodb.get_suite(suite.suite_id) is None
        assert len(dynamodb.get_cases(suite.suite_id)) == 0


class TestCreateCase:
    def test_create_case(self, aws_setup):
        suite = Suite(name="Parent Suite")
        dynamodb.create_suite(suite)

        case = Case(suite_id=suite.suite_id, input="What is 2+2?")
        result = dynamodb.create_case(case)

        assert result.case_id == case.case_id
        assert result.suite_id == suite.suite_id
        assert result.input == "What is 2+2?"

    def test_create_case_with_optional_fields(self, aws_setup):
        suite = Suite(name="Parent Suite")
        dynamodb.create_suite(suite)

        case = Case(
            suite_id=suite.suite_id,
            input="test",
            expected_behavior="Should return 4",
            tags=["math", "basic"],
        )
        result = dynamodb.create_case(case)

        assert result.expected_behavior == "Should return 4"
        assert result.tags == ["math", "basic"]

    def test_create_case_verifies_dynamodb_item(self, aws_setup):
        suite = Suite(name="Parent Suite")
        dynamodb.create_suite(suite)

        case = Case(suite_id=suite.suite_id, input="test input")
        dynamodb.create_case(case)

        table = dynamodb.get_table()
        response = table.get_item(
            Key={"PK": f"SUITE#{suite.suite_id}", "SK": f"CASE#{case.case_id}"}
        )
        item = response["Item"]
        assert item["input"] == "test input"
        assert item["PK"] == f"SUITE#{suite.suite_id}"
        assert item["SK"] == f"CASE#{case.case_id}"


class TestGetCases:
    def test_get_cases_empty(self, aws_setup):
        suite = Suite(name="Empty Suite")
        dynamodb.create_suite(suite)

        result = dynamodb.get_cases(suite.suite_id)
        assert result == []

    def test_get_cases_multiple(self, aws_setup):
        suite = Suite(name="Suite with Cases")
        dynamodb.create_suite(suite)

        case1 = Case(suite_id=suite.suite_id, input="input 1")
        case2 = Case(suite_id=suite.suite_id, input="input 2")
        dynamodb.create_case(case1)
        dynamodb.create_case(case2)

        result = dynamodb.get_cases(suite.suite_id)
        assert len(result) == 2
        inputs = {c.input for c in result}
        assert inputs == {"input 1", "input 2"}

    def test_get_cases_only_returns_cases(self, aws_setup):
        suite = Suite(name="Suite")
        dynamodb.create_suite(suite)

        case = Case(suite_id=suite.suite_id, input="case input")
        dynamodb.create_case(case)

        # Ensure only cases are returned, not META items
        result = dynamodb.get_cases(suite.suite_id)
        assert len(result) == 1
        assert result[0].input == "case input"


class TestGetCase:
    def test_get_existing_case(self, aws_setup):
        suite = Suite(name="Suite")
        dynamodb.create_suite(suite)

        case = Case(suite_id=suite.suite_id, input="test")
        dynamodb.create_case(case)

        result = dynamodb.get_case(suite.suite_id, case.case_id)
        assert result is not None
        assert result.input == "test"
        assert result.case_id == case.case_id

    def test_get_nonexistent_case(self, aws_setup):
        result = dynamodb.get_case("suite-id", "case-id")
        assert result is None


class TestUpdateCase:
    def test_update_case_input(self, aws_setup):
        suite = Suite(name="Suite")
        dynamodb.create_suite(suite)

        case = Case(suite_id=suite.suite_id, input="old input")
        dynamodb.create_case(case)

        result = dynamodb.update_case(suite.suite_id, case.case_id, "new input")
        assert result.input == "new input"
        assert result.case_id == case.case_id

    def test_update_case_expected_behavior(self, aws_setup):
        suite = Suite(name="Suite")
        dynamodb.create_suite(suite)

        case = Case(suite_id=suite.suite_id, input="test")
        dynamodb.create_case(case)

        result = dynamodb.update_case(
            suite.suite_id, case.case_id, "test", expected_behavior="new behavior"
        )
        assert result.expected_behavior == "new behavior"

    def test_update_case_tags(self, aws_setup):
        suite = Suite(name="Suite")
        dynamodb.create_suite(suite)

        case = Case(suite_id=suite.suite_id, input="test")
        dynamodb.create_case(case)

        result = dynamodb.update_case(
            suite.suite_id, case.case_id, "test", tags=["new", "tags"]
        )
        assert result.tags == ["new", "tags"]

    def test_update_case_all_fields(self, aws_setup):
        suite = Suite(name="Suite")
        dynamodb.create_suite(suite)

        case = Case(suite_id=suite.suite_id, input="old")
        dynamodb.create_case(case)

        result = dynamodb.update_case(
            suite.suite_id,
            case.case_id,
            "updated input",
            expected_behavior="updated behavior",
            tags=["updated"],
        )
        assert result.input == "updated input"
        assert result.expected_behavior == "updated behavior"
        assert result.tags == ["updated"]


class TestDeleteCase:
    def test_delete_case(self, aws_setup):
        suite = Suite(name="Suite")
        dynamodb.create_suite(suite)

        case = Case(suite_id=suite.suite_id, input="to delete")
        dynamodb.create_case(case)

        result = dynamodb.delete_case(suite.suite_id, case.case_id)
        assert result is True

        # Verify case is gone
        retrieved = dynamodb.get_case(suite.suite_id, case.case_id)
        assert retrieved is None

    def test_delete_case_does_not_affect_suite(self, aws_setup):
        suite = Suite(name="Suite")
        dynamodb.create_suite(suite)

        case = Case(suite_id=suite.suite_id, input="test")
        dynamodb.create_case(case)

        dynamodb.delete_case(suite.suite_id, case.case_id)

        # Suite should still exist
        retrieved = dynamodb.get_suite(suite.suite_id)
        assert retrieved is not None
        assert retrieved.name == "Suite"


class TestGetTable:
    def test_get_table_default_name(self, aws_setup):
        os.environ.pop("TABLE_NAME", None)
        table = dynamodb.get_table()
        assert table.name == "PromptLens"

    def test_get_table_custom_name(self, aws_setup):
        os.environ["TABLE_NAME"] = "CustomTable"
        table = dynamodb.get_table()
        assert table.name == "CustomTable"
