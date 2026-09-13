"""Tests for Run operations."""

import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from moto import mock_aws
import boto3
from src.handlers.api.models import Run, RunCaseResult
from src.handlers.api.dynamodb import (
    create_run,
    get_run,
    list_runs,
    update_run_status,
    create_run_case_result,
    get_run_case_results,
    delete_run,
)


@pytest.fixture
def aws_setup():
    """Set up AWS mocks."""
    with mock_aws():
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        os.environ["TABLE_NAME"] = "PromptLens"

        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
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

        yield table


class TestCreateRun:
    """Tests for create_run."""

    def test_create_run(self, aws_setup):
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            baseline_prompt="Be helpful",
            candidate_prompt="Be concise and helpful",
            rubric="Score on helpfulness and clarity",
        )

        result = create_run(run)

        assert result.run_id == run.run_id
        assert result.suite_id == "suite-1"
        assert result.status == "RUNNING"

    def test_create_run_verifies_dynamodb_item(self, aws_setup):
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            baseline_prompt="Be helpful",
            candidate_prompt="Be concise and helpful",
            rubric="Score on helpfulness and clarity",
        )

        create_run(run)

        table = aws_setup
        response = table.get_item(Key={"PK": f"RUN#{run.run_id}", "SK": "META"})

        item = response.get("Item")
        assert item is not None
        assert item["suite_id"] == "suite-1"
        assert item["model_id"] == "anthropic.claude-3-sonnet-20240229-v1:0"


class TestGetRun:
    """Tests for get_run."""

    def test_get_existing_run(self, aws_setup):
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            baseline_prompt="Be helpful",
            candidate_prompt="Be concise and helpful",
            rubric="Score on helpfulness and clarity",
        )

        create_run(run)
        result = get_run(run.run_id)

        assert result is not None
        assert result.run_id == run.run_id

    def test_get_nonexistent_run(self, aws_setup):
        result = get_run("nonexistent")

        assert result is None


class TestListRuns:
    """Tests for list_runs."""

    def test_list_empty(self, aws_setup):
        result = list_runs()

        assert result == []

    def test_list_multiple_runs(self, aws_setup):
        run1 = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            baseline_prompt="Be helpful",
            candidate_prompt="Be concise and helpful",
            rubric="Score on helpfulness and clarity",
        )
        run2 = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            baseline_prompt="Be helpful",
            candidate_prompt="Be concise and helpful",
            rubric="Score on helpfulness and clarity",
        )

        create_run(run1)
        create_run(run2)

        result = list_runs()

        assert len(result) == 2


class TestUpdateRunStatus:
    """Tests for update_run_status."""

    def test_update_status_to_completed(self, aws_setup):
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            baseline_prompt="Be helpful",
            candidate_prompt="Be concise and helpful",
            rubric="Score on helpfulness and clarity",
        )

        create_run(run)
        result = update_run_status(run.run_id, "COMPLETED")

        assert result.status == "COMPLETED"
        assert result.completed_at is not None

    def test_update_status_to_failed(self, aws_setup):
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            baseline_prompt="Be helpful",
            candidate_prompt="Be concise and helpful",
            rubric="Score on helpfulness and clarity",
        )

        create_run(run)
        result = update_run_status(run.run_id, "FAILED")

        assert result.status == "FAILED"
        assert result.completed_at is not None


class TestCreateRunCaseResult:
    """Tests for create_run_case_result."""

    def test_create_result(self, aws_setup):
        result = RunCaseResult(
            run_id="run-1",
            case_id="case-1",
            baseline_output="Baseline text",
            candidate_output="Candidate text",
            baseline_score=4,
            candidate_score=5,
            baseline_rationale="Good",
            candidate_rationale="Excellent",
            baseline_latency_ms=1000.0,
            candidate_latency_ms=1200.0,
            classification="Improved",
        )

        created = create_run_case_result(result)

        assert created.run_id == "run-1"
        assert created.case_id == "case-1"
        assert created.classification == "Improved"

    def test_create_result_with_error(self, aws_setup):
        result = RunCaseResult(
            run_id="run-1",
            case_id="case-1",
            error="Model invocation failed",
            classification="Failed",
        )

        created = create_run_case_result(result)

        assert created.error == "Model invocation failed"
        assert created.classification == "Failed"


class TestGetRunCaseResults:
    """Tests for get_run_case_results."""

    def test_get_results_empty(self, aws_setup):
        result = get_run_case_results("run-1")

        assert result == []

    def test_get_results_multiple(self, aws_setup):
        result1 = RunCaseResult(
            run_id="run-1",
            case_id="case-1",
            classification="Improved",
        )
        result2 = RunCaseResult(
            run_id="run-1",
            case_id="case-2",
            classification="Regressed",
        )

        create_run_case_result(result1)
        create_run_case_result(result2)

        results = get_run_case_results("run-1")

        assert len(results) == 2


class TestDeleteRun:
    """Tests for delete_run."""

    def test_delete_run(self, aws_setup):
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            baseline_prompt="Be helpful",
            candidate_prompt="Be concise and helpful",
            rubric="Score on helpfulness and clarity",
        )

        create_run(run)
        result = delete_run(run.run_id)

        assert result is True
        assert get_run(run.run_id) is None


class TestRunRoutes:
    """Tests for Run route handlers."""

    def test_handle_runs_get(self, aws_setup):
        from src.handlers.api.routes.runs import handle_runs

        event = {"httpMethod": "GET"}
        result = handle_runs(event)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body == []

    def test_handle_runs_post_missing_fields(self, aws_setup):
        from src.handlers.api.routes.runs import handle_runs

        event = {
            "httpMethod": "POST",
            "body": json.dumps({}),
        }
        result = handle_runs(event)

        assert result["statusCode"] == 400

    def test_handle_run_by_id_not_found(self, aws_setup):
        from src.handlers.api.routes.runs import handle_run_by_id

        event = {
            "httpMethod": "GET",
            "pathParameters": {"runId": "nonexistent"},
        }
        result = handle_run_by_id(event)

        assert result["statusCode"] == 404
