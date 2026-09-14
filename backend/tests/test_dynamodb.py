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


class TestCreateRun:
    def test_create_run(self, aws_setup):
        from src.handlers.api.models import Run

        run = Run(
            suite_id="suite-123",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="You are helpful",
            candidate_prompt="You are very helpful",
            rubric="Rate the response 1-5",
        )
        result = dynamodb.create_run(run)

        assert result.run_id == run.run_id
        assert result.suite_id == "suite-123"
        assert result.model_id == "anthropic.claude-3-sonnet"
        assert result.status == "RUNNING"

    def test_create_run_verifies_dynamodb_item(self, aws_setup):
        from src.handlers.api.models import Run

        run = Run(
            suite_id="suite-abc",
            model_id="anthropic.claude-3-opus",
            baseline_prompt="baseline",
            candidate_prompt="candidate",
            rubric="rubric",
        )
        dynamodb.create_run(run)

        table = dynamodb.get_table()
        response = table.get_item(Key={"PK": f"RUN#{run.run_id}", "SK": "META"})
        item = response["Item"]
        assert item["suite_id"] == "suite-abc"
        assert item["model_id"] == "anthropic.claude-3-opus"
        assert item["baseline_prompt"] == "baseline"


class TestGetRun:
    def test_get_existing_run(self, aws_setup):
        from src.handlers.api.models import Run

        run = Run(
            suite_id="suite-1",
            model_id="model-1",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
        )
        dynamodb.create_run(run)

        result = dynamodb.get_run(run.run_id)
        assert result is not None
        assert result.run_id == run.run_id
        assert result.suite_id == "suite-1"
        assert result.status == "RUNNING"

    def test_get_nonexistent_run(self, aws_setup):
        result = dynamodb.get_run("nonexistent-id")
        assert result is None

    def test_get_run_with_optional_fields(self, aws_setup):
        from src.handlers.api.models import Run

        run = Run(
            suite_id="s",
            model_id="m",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
            temperature=0.5,
            max_tokens=2048,
        )
        dynamodb.create_run(run)

        result = dynamodb.get_run(run.run_id)
        assert result.temperature == 0.5
        assert result.max_tokens == 2048


class TestListRuns:
    def test_list_empty(self, aws_setup):
        result = dynamodb.list_runs()
        assert result == []

    def test_list_multiple_runs(self, aws_setup):
        from src.handlers.api.models import Run

        run1 = Run(
            suite_id="s1",
            model_id="m1",
            baseline_prompt="bp1",
            candidate_prompt="cp1",
            rubric="r1",
        )
        run2 = Run(
            suite_id="s2",
            model_id="m2",
            baseline_prompt="bp2",
            candidate_prompt="cp2",
            rubric="r2",
        )
        dynamodb.create_run(run1)
        dynamodb.create_run(run2)

        result = dynamodb.list_runs()
        assert len(result) == 2
        run_ids = {r.run_id for r in result}
        assert run_ids == {run1.run_id, run2.run_id}

    def test_list_runs_only_returns_runs(self, aws_setup):
        from src.handlers.api.models import Run, Suite

        # Create a suite (also has SK=META)
        suite = Suite(name="Test Suite")
        dynamodb.create_suite(suite)

        # Create a run
        run = Run(
            suite_id=suite.suite_id,
            model_id="model",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
        )
        dynamodb.create_run(run)

        result = dynamodb.list_runs()
        assert len(result) == 1
        assert result[0].run_id == run.run_id


class TestUpdateRunStatus:
    def test_update_to_completed(self, aws_setup):
        from src.handlers.api.models import Run

        run = Run(
            suite_id="s",
            model_id="m",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
        )
        dynamodb.create_run(run)

        result = dynamodb.update_run_status(run.run_id, "COMPLETED")
        assert result.status == "COMPLETED"
        assert result.completed_at is not None

    def test_update_to_running(self, aws_setup):
        from src.handlers.api.models import Run

        run = Run(
            suite_id="s",
            model_id="m",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
        )
        dynamodb.create_run(run)

        result = dynamodb.update_run_status(run.run_id, "RUNNING")
        assert result.status == "RUNNING"
        assert result.completed_at is None

    def test_update_to_failed(self, aws_setup):
        from src.handlers.api.models import Run

        run = Run(
            suite_id="s",
            model_id="m",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
        )
        dynamodb.create_run(run)

        result = dynamodb.update_run_status(run.run_id, "FAILED")
        assert result.status == "FAILED"
        assert result.completed_at is not None

    def test_update_to_partial(self, aws_setup):
        from src.handlers.api.models import Run

        run = Run(
            suite_id="s",
            model_id="m",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
        )
        dynamodb.create_run(run)

        result = dynamodb.update_run_status(run.run_id, "PARTIAL")
        assert result.status == "PARTIAL"
        assert result.completed_at is not None


class TestCreateRunCaseResult:
    def test_create_result(self, aws_setup):
        from src.handlers.api.models import Run, RunCaseResult

        run = Run(
            suite_id="s",
            model_id="m",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
        )
        dynamodb.create_run(run)

        result = RunCaseResult(
            run_id=run.run_id,
            case_id="case-1",
            baseline_output="baseline out",
            candidate_output="candidate out",
            baseline_score=3,
            candidate_score=4,
            classification="Improved",
        )
        saved = dynamodb.create_run_case_result(result)

        assert saved.run_id == run.run_id
        assert saved.case_id == "case-1"
        assert saved.classification == "Improved"

    def test_create_result_with_optional_fields(self, aws_setup):
        from decimal import Decimal
        from src.handlers.api.models import Run, RunCaseResult

        run = Run(
            suite_id="s",
            model_id="m",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
        )
        dynamodb.create_run(run)

        result = RunCaseResult(
            run_id=run.run_id,
            case_id="case-2",
            baseline_output="base",
            candidate_output="cand",
            baseline_score=2,
            candidate_score=5,
            baseline_rationale="rationale base",
            candidate_rationale="rationale cand",
            baseline_latency_ms=150.5,
            candidate_latency_ms=200.3,
            classification="Improved",
        )
        saved = dynamodb.create_run_case_result(result)

        table = dynamodb.get_table()
        response = table.get_item(Key={"PK": f"RUN#{run.run_id}", "SK": "CASE#case-2"})
        item = response["Item"]
        assert item["baseline_rationale"] == "rationale base"
        assert item["candidate_latency_ms"] == Decimal("200.3")

    def test_create_result_with_error(self, aws_setup):
        from src.handlers.api.models import Run, RunCaseResult

        run = Run(
            suite_id="s",
            model_id="m",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
        )
        dynamodb.create_run(run)

        result = RunCaseResult(
            run_id=run.run_id,
            case_id="case-3",
            classification="Failed",
            error="Timeout error",
        )
        saved = dynamodb.create_run_case_result(result)
        assert saved.error == "Timeout error"


class TestGetRunCaseResults:
    def test_get_results_empty(self, aws_setup):
        from src.handlers.api.models import Run

        run = Run(
            suite_id="s",
            model_id="m",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
        )
        dynamodb.create_run(run)

        result = dynamodb.get_run_case_results(run.run_id)
        assert result == []

    def test_get_results_multiple(self, aws_setup):
        from src.handlers.api.models import Run, RunCaseResult

        run = Run(
            suite_id="s",
            model_id="m",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
        )
        dynamodb.create_run(run)

        result1 = RunCaseResult(
            run_id=run.run_id, case_id="c1", classification="Unchanged"
        )
        result2 = RunCaseResult(
            run_id=run.run_id, case_id="c2", classification="Improved"
        )
        dynamodb.create_run_case_result(result1)
        dynamodb.create_run_case_result(result2)

        results = dynamodb.get_run_case_results(run.run_id)
        assert len(results) == 2
        case_ids = {r.case_id for r in results}
        assert case_ids == {"c1", "c2"}

    def test_get_results_only_for_specified_run(self, aws_setup):
        from src.handlers.api.models import Run, RunCaseResult

        run1 = Run(
            suite_id="s",
            model_id="m",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
        )
        run2 = Run(
            suite_id="s",
            model_id="m",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
        )
        dynamodb.create_run(run1)
        dynamodb.create_run(run2)

        r1 = RunCaseResult(run_id=run1.run_id, case_id="c1", classification="Unchanged")
        r2 = RunCaseResult(run_id=run2.run_id, case_id="c2", classification="Improved")
        dynamodb.create_run_case_result(r1)
        dynamodb.create_run_case_result(r2)

        results = dynamodb.get_run_case_results(run1.run_id)
        assert len(results) == 1
        assert results[0].run_id == run1.run_id


class TestDeleteRun:
    def test_delete_run(self, aws_setup):
        from src.handlers.api.models import Run

        run = Run(
            suite_id="s",
            model_id="m",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
        )
        dynamodb.create_run(run)

        result = dynamodb.delete_run(run.run_id)
        assert result is True
        assert dynamodb.get_run(run.run_id) is None

    def test_delete_run_with_results(self, aws_setup):
        from src.handlers.api.models import Run, RunCaseResult

        run = Run(
            suite_id="s",
            model_id="m",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
        )
        dynamodb.create_run(run)

        result1 = RunCaseResult(
            run_id=run.run_id, case_id="c1", classification="Unchanged"
        )
        dynamodb.create_run_case_result(result1)

        # Verify results exist
        results = dynamodb.get_run_case_results(run.run_id)
        assert len(results) == 1

        # Delete run
        dynamodb.delete_run(run.run_id)

        # Verify run and results are gone
        assert dynamodb.get_run(run.run_id) is None
        assert len(dynamodb.get_run_case_results(run.run_id)) == 0

    def test_delete_run_does_not_affect_other_runs(self, aws_setup):
        from src.handlers.api.models import Run, RunCaseResult

        run1 = Run(
            suite_id="s",
            model_id="m",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
        )
        run2 = Run(
            suite_id="s",
            model_id="m",
            baseline_prompt="bp",
            candidate_prompt="cp",
            rubric="r",
        )
        dynamodb.create_run(run1)
        dynamodb.create_run(run2)

        r1 = RunCaseResult(run_id=run1.run_id, case_id="c1", classification="Unchanged")
        r2 = RunCaseResult(run_id=run2.run_id, case_id="c2", classification="Improved")
        dynamodb.create_run_case_result(r1)
        dynamodb.create_run_case_result(r2)

        # Delete run1
        dynamodb.delete_run(run1.run_id)

        # run2 should still exist
        assert dynamodb.get_run(run2.run_id) is not None
        results = dynamodb.get_run_case_results(run2.run_id)
        assert len(results) == 1
