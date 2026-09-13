"""Tests for Run route handlers."""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.handlers.api.models import Suite, Case, Run, RunCaseResult
from src.handlers.api import dynamodb
from src.handlers.api.routes.runs import (
    handle_runs,
    handle_run_by_id,
    execute_run,
    MAX_CASES_PER_RUN,
)
from tests.conftest import make_event


class TestHandleRuns:
    def test_get_list_runs_empty(self, aws_setup):
        event = make_event("GET")
        response = handle_runs(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body == []

    def test_get_list_runs(self, aws_setup):
        suite = dynamodb.create_suite(Suite(name="Test Suite"))
        case = Case(suite_id=suite.suite_id, input="What is 2+2?")
        dynamodb.create_case(case)

        run = Run(
            suite_id=suite.suite_id,
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            baseline_prompt="Answer clearly",
            candidate_prompt="Answer concisely",
            rubric="Score based on accuracy",
        )
        dynamodb.create_run(run)

        event = make_event("GET")
        response = handle_runs(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body) == 1
        assert body[0]["runId"] == run.run_id

    def test_post_create_run_missing_fields(self, aws_setup):
        event = make_event("POST", body={})
        response = handle_runs(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "required" in body["message"]

    def test_post_create_run_invalid_json(self, aws_setup):
        event = make_event("POST", body="not json")
        response = handle_runs(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["message"] == "Invalid JSON"

    def test_post_create_run_suite_not_found(self, aws_setup):
        event = make_event(
            "POST",
            body={
                "suiteId": "nonexistent",
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "baselinePrompt": "Answer clearly",
                "candidatePrompt": "Answer concisely",
                "rubric": "Score based on accuracy",
            },
        )
        response = handle_runs(event)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["message"] == "Suite not found"

    def test_post_create_run_suite_no_cases(self, aws_setup):
        suite = dynamodb.create_suite(Suite(name="Empty Suite"))

        event = make_event(
            "POST",
            body={
                "suiteId": suite.suite_id,
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "baselinePrompt": "Answer clearly",
                "candidatePrompt": "Answer concisely",
                "rubric": "Score based on accuracy",
            },
        )
        response = handle_runs(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["message"] == "Suite has no cases"

    @patch("src.handlers.api.routes.runs.execute_run")
    def test_post_create_run_success(self, mock_execute, aws_setup):
        suite = dynamodb.create_suite(Suite(name="Test Suite"))
        case = Case(suite_id=suite.suite_id, input="What is 2+2?")
        dynamodb.create_case(case)

        event = make_event(
            "POST",
            body={
                "suiteId": suite.suite_id,
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "baselinePrompt": "Answer clearly",
                "candidatePrompt": "Answer concisely",
                "rubric": "Score based on accuracy",
                "temperature": 0.5,
                "maxTokens": 512,
            },
        )
        response = handle_runs(event)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["suiteId"] == suite.suite_id
        assert body["modelId"] == "anthropic.claude-3-haiku-20240307-v1:0"
        assert body["status"] == "RUNNING"
        assert body["temperature"] == 0.5
        assert body["maxTokens"] == 512

    def test_method_not_allowed(self, aws_setup):
        event = make_event("DELETE")
        response = handle_runs(event)

        assert response["statusCode"] == 405
        body = json.loads(response["body"])
        assert body["message"] == "Method not allowed"


class TestHandleRunById:
    def test_get_run_found(self, aws_setup):
        suite = dynamodb.create_suite(Suite(name="Test Suite"))
        case = Case(suite_id=suite.suite_id, input="What is 2+2?")
        dynamodb.create_case(case)

        run = Run(
            suite_id=suite.suite_id,
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            baseline_prompt="Answer clearly",
            candidate_prompt="Answer concisely",
            rubric="Score based on accuracy",
        )
        dynamodb.create_run(run)

        result = RunCaseResult(
            run_id=run.run_id,
            case_id=case.case_id,
            baseline_output="4",
            candidate_output="Four",
            baseline_score=5,
            candidate_score=4,
            classification="Regressed",
        )
        dynamodb.create_run_case_result(result)

        event = make_event("GET", path_params={"runId": run.run_id})
        response = handle_run_by_id(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["runId"] == run.run_id
        assert "results" in body
        assert len(body["results"]) == 1
        assert body["results"][0]["classification"] == "Regressed"

    def test_get_run_not_found(self, aws_setup):
        event = make_event("GET", path_params={"runId": "nonexistent"})
        response = handle_run_by_id(event)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["message"] == "Run not found"

    def test_get_run_missing_id(self, aws_setup):
        event = make_event("GET", path_params={})
        response = handle_run_by_id(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["message"] == "runId is required"

    def test_delete_run(self, aws_setup):
        suite = dynamodb.create_suite(Suite(name="Test Suite"))
        run = Run(
            suite_id=suite.suite_id,
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            baseline_prompt="Answer clearly",
            candidate_prompt="Answer concisely",
            rubric="Score based on accuracy",
        )
        dynamodb.create_run(run)

        event = make_event("DELETE", path_params={"runId": run.run_id})
        response = handle_run_by_id(event)

        assert response["statusCode"] == 204
        assert dynamodb.get_run(run.run_id) is None

    def test_delete_run_not_found(self, aws_setup):
        event = make_event("DELETE", path_params={"runId": "nonexistent"})
        response = handle_run_by_id(event)

        assert response["statusCode"] == 404

    def test_method_not_allowed(self, aws_setup):
        event = make_event("POST", path_params={"runId": "some-id"})
        response = handle_run_by_id(event)

        assert response["statusCode"] == 405


class TestExecuteRun:
    @patch("src.handlers.api.routes.runs.create_run_case_result")
    @patch("src.handlers.api.routes.runs.update_run_status")
    @patch("src.handlers.api.routes.runs.classify_result", return_value="Improved")
    @patch("src.handlers.api.routes.runs.evaluate_output")
    @patch("src.handlers.api.routes.runs.invoke_model")
    def test_execute_run_successful(
        self,
        mock_invoke,
        mock_evaluate,
        mock_classify,
        mock_update_status,
        mock_create_result,
    ):
        mock_invoke.return_value = ("test output", 100.0)
        mock_evaluate.return_value = {"score": 4, "rationale": "Good"}

        run = Run(
            suite_id="suite-123",
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            baseline_prompt="Answer clearly",
            candidate_prompt="Answer concisely",
            rubric="Score based on accuracy",
        )

        case = Case(suite_id="suite-123", input="What is 2+2?")

        execute_run(run, [case])

        assert mock_create_result.call_count == 1
        result = mock_create_result.call_args[0][0]
        assert result.classification == "Improved"
        mock_update_status.assert_called_once_with(run.run_id, "COMPLETED")

    @patch("src.handlers.api.routes.runs.create_run_case_result")
    @patch("src.handlers.api.routes.runs.update_run_status")
    @patch(
        "src.handlers.api.routes.runs.invoke_model", side_effect=Exception("API error")
    )
    def test_execute_run_case_failure(
        self,
        mock_invoke,
        mock_update_status,
        mock_create_result,
    ):
        run = Run(
            suite_id="suite-123",
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            baseline_prompt="Answer clearly",
            candidate_prompt="Answer concisely",
            rubric="Score based on accuracy",
        )

        case = Case(suite_id="suite-123", input="What is 2+2?")

        execute_run(run, [case])

        result = mock_create_result.call_args[0][0]
        assert result.classification == "Failed"
        assert result.error == "API error"
        mock_update_status.assert_called_once_with(run.run_id, "FAILED")

    @patch("src.handlers.api.routes.runs.create_run_case_result")
    @patch("src.handlers.api.routes.runs.update_run_status")
    @patch("src.handlers.api.routes.runs.classify_result", return_value="Improved")
    @patch("src.handlers.api.routes.runs.evaluate_output")
    @patch("src.handlers.api.routes.runs.invoke_model")
    def test_execute_run_partial_success(
        self,
        mock_invoke,
        mock_evaluate,
        mock_classify,
        mock_update_status,
        mock_create_result,
    ):
        # Case 1: succeeds (baseline + candidate), Case 2: fails on baseline
        mock_invoke.side_effect = [
            ("output 1", 100.0),
            ("output 2", 100.0),
            Exception("API error"),
        ]
        mock_evaluate.return_value = {"score": 4, "rationale": "Good"}

        run = Run(
            suite_id="suite-123",
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            baseline_prompt="Answer clearly",
            candidate_prompt="Answer concisely",
            rubric="Score based on accuracy",
        )

        cases = [
            Case(suite_id="suite-123", input="Question 1"),
            Case(suite_id="suite-123", input="Question 2"),
        ]

        execute_run(run, cases)

        assert mock_create_result.call_count == 2
        first_result = mock_create_result.call_args_list[0][0][0]
        assert first_result.classification == "Improved"
        second_result = mock_create_result.call_args_list[1][0][0]
        assert second_result.classification == "Failed"
        mock_update_status.assert_called_once_with(run.run_id, "PARTIAL")


class TestMaxCasesPerRun:
    def test_max_cases_constant(self):
        assert MAX_CASES_PER_RUN == 3
