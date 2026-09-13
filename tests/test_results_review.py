"""Tests for Results & Review features."""

import json
import os
import pytest
from moto import mock_aws
import boto3
from src.handlers.api.models import Run, RunCaseResult
from src.handlers.api.dynamodb import (
    create_run,
    create_run_case_result,
    get_run,
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

        conn = boto3.resource("dynamodb", region_name="us-east-1")
        conn.create_table(
            TableName="PromptLens",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield


class TestRunSummary:
    """Test summary statistics in run response."""

    def test_run_response_includes_summary(self, aws_setup):
        """Run response should include summary counts per classification."""
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="Baseline prompt",
            candidate_prompt="Candidate prompt",
            rubric="Test rubric",
        )
        created_run = create_run(run)

        # Create results with different classifications
        for i, classification in enumerate(["Improved", "Regressed", "Unchanged"]):
            result = RunCaseResult(
                run_id=created_run.run_id,
                case_id=f"case-{i}",
                baseline_output=f"Baseline output {i}",
                candidate_output=f"Candidate output {i}",
                baseline_score=3,
                candidate_score=4
                if classification == "Improved"
                else 2
                if classification == "Regressed"
                else 3,
                baseline_rationale="Baseline rationale",
                candidate_rationale="Candidate rationale",
                baseline_latency_ms=100,
                candidate_latency_ms=120,
                classification=classification,
            )
            create_run_case_result(result)

        # Get run with results
        from src.handlers.api.routes.runs import get_run_handler

        response = get_run_handler(created_run.run_id)
        body = json.loads(response["body"])

        # Verify summary exists
        assert "summary" in body
        assert body["summary"]["total"] == 3
        assert body["summary"]["improved"] == 1
        assert body["summary"]["regressed"] == 1
        assert body["summary"]["unchanged"] == 1
        assert body["summary"]["needsReview"] == 0
        assert body["summary"]["failed"] == 0

    def test_run_response_summary_with_errors(self, aws_setup):
        """Summary should count Failed classifications from errors."""
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="Baseline prompt",
            candidate_prompt="Candidate prompt",
            rubric="Test rubric",
        )
        created_run = create_run(run)

        # Create a failed result
        result = RunCaseResult(
            run_id=created_run.run_id,
            case_id="case-0",
            error="Bedrock invocation failed",
            classification="Failed",
        )
        create_run_case_result(result)

        from src.handlers.api.routes.runs import get_run_handler

        response = get_run_handler(created_run.run_id)
        body = json.loads(response["body"])

        assert body["summary"]["failed"] == 1
        assert body["summary"]["total"] == 1
