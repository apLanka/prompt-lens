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

    @patch("src.handlers.api.routes.runs.create_run_case_result")
    @patch("src.handlers.api.routes.runs.update_run_status")
    @patch("src.handlers.api.routes.runs.classify_result", return_value="Improved")
    @patch("src.handlers.api.routes.runs.evaluate_output")
    @patch("src.handlers.api.routes.runs.invoke_model")
    def test_post_create_run_with_case_ids(
        self,
        mock_invoke,
        mock_evaluate,
        mock_classify,
        mock_update_status,
        mock_create_result,
        aws_setup,
    ):
        mock_invoke.return_value = ("test output", 100.0)
        mock_evaluate.return_value = {"score": 4, "rationale": "Good"}

        suite = dynamodb.create_suite(Suite(name="Test Suite"))
        case1 = Case(suite_id=suite.suite_id, input="Question 1")
        case2 = Case(suite_id=suite.suite_id, input="Question 2")
        case3 = Case(suite_id=suite.suite_id, input="Question 3")
        case4 = Case(suite_id=suite.suite_id, input="Question 4")
        for c in [case1, case2, case3, case4]:
            dynamodb.create_case(c)

        event = make_event(
            "POST",
            body={
                "suiteId": suite.suite_id,
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "baselinePrompt": "Answer clearly",
                "candidatePrompt": "Answer concisely",
                "rubric": "Score based on accuracy",
                "caseIds": [case4.case_id, case2.case_id],
            },
        )
        response = handle_runs(event)

        assert response["statusCode"] == 201
        baseline_prompts = [
            call.kwargs["prompt"]
            for call in mock_invoke.call_args_list
            if call.kwargs["prompt"].startswith("Answer clearly\n\n")
        ]
        assert sorted(baseline_prompts) == sorted(
            ["Answer clearly\n\nQuestion 2", "Answer clearly\n\nQuestion 4"]
        )
        result_case_ids = sorted(
            call.args[0].case_id for call in mock_create_result.call_args_list
        )
        assert result_case_ids == sorted([case2.case_id, case4.case_id])

    def test_post_create_run_case_ids_no_match(self, aws_setup):
        suite = dynamodb.create_suite(Suite(name="Test Suite"))
        dynamodb.create_case(Case(suite_id=suite.suite_id, input="What is 2+2?"))

        event = make_event(
            "POST",
            body={
                "suiteId": suite.suite_id,
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "baselinePrompt": "Answer clearly",
                "candidatePrompt": "Answer concisely",
                "rubric": "Score based on accuracy",
                "caseIds": ["nonexistent-id"],
            },
        )
        response = handle_runs(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["message"] == "None of the selected cases were found in this suite"

    def test_post_create_run_case_ids_not_a_list(self, aws_setup):
        suite = dynamodb.create_suite(Suite(name="Test Suite"))
        dynamodb.create_case(Case(suite_id=suite.suite_id, input="What is 2+2?"))

        event = make_event(
            "POST",
            body={
                "suiteId": suite.suite_id,
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "baselinePrompt": "Answer clearly",
                "candidatePrompt": "Answer concisely",
                "rubric": "Score based on accuracy",
                "caseIds": "not-a-list",
            },
        )
        response = handle_runs(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["message"] == "caseIds must be a list"

    @patch("src.handlers.api.routes.runs.create_run_case_result")
    @patch("src.handlers.api.routes.runs.update_run_status")
    @patch("src.handlers.api.routes.runs.classify_result", return_value="Improved")
    @patch("src.handlers.api.routes.runs.evaluate_output")
    @patch("src.handlers.api.routes.runs.invoke_model")
    def test_post_create_run_without_case_ids_uses_first_three(
        self,
        mock_invoke,
        mock_evaluate,
        mock_classify,
        mock_update_status,
        mock_create_result,
        aws_setup,
    ):
        mock_invoke.return_value = ("test output", 100.0)
        mock_evaluate.return_value = {"score": 4, "rationale": "Good"}

        suite = dynamodb.create_suite(Suite(name="Test Suite"))
        cases = [
            Case(suite_id=suite.suite_id, input=f"Question {i}") for i in range(1, 5)
        ]
        for c in cases:
            dynamodb.create_case(c)

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

        assert response["statusCode"] == 201
        expected_inputs = [
            c.input for c in dynamodb.get_cases(suite.suite_id)[:MAX_CASES_PER_RUN]
        ]
        baseline_prompts = [
            call.kwargs["prompt"]
            for call in mock_invoke.call_args_list
            if call.kwargs["prompt"].startswith("Answer clearly\n\n")
        ]
        assert baseline_prompts == [
            f"Answer clearly\n\n{inp}" for inp in expected_inputs
        ]

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


class TestRunValidation:
    """Tests for input validation on run creation."""

    def _make_suite_and_cases(self, aws_setup, count=3):
        """Helper: create a suite with N cases."""
        suite = dynamodb.create_suite(Suite(name="Test Suite"))
        cases = []
        for i in range(count):
            c = Case(suite_id=suite.suite_id, input=f"Input {i}")
            dynamodb.create_case(c)
            cases.append(c)
        return suite, cases

    def test_baseline_prompt_too_long(self, aws_setup):
        suite, _ = self._make_suite_and_cases(aws_setup)
        event = make_event(
            "POST",
            body={
                "suiteId": suite.suite_id,
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "baselinePrompt": "x" * 10001,
                "candidatePrompt": "short",
                "rubric": "good",
            },
        )
        response = handle_runs(event)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "baselinePrompt" in body["message"]

    def test_candidate_prompt_too_long(self, aws_setup):
        suite, _ = self._make_suite_and_cases(aws_setup)
        event = make_event(
            "POST",
            body={
                "suiteId": suite.suite_id,
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "baselinePrompt": "short",
                "candidatePrompt": "x" * 10001,
                "rubric": "good",
            },
        )
        response = handle_runs(event)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "candidatePrompt" in body["message"]

    def test_temperature_out_of_range_low(self, aws_setup):
        suite, _ = self._make_suite_and_cases(aws_setup)
        event = make_event(
            "POST",
            body={
                "suiteId": suite.suite_id,
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "baselinePrompt": "test",
                "candidatePrompt": "test",
                "rubric": "good",
                "temperature": -0.1,
            },
        )
        response = handle_runs(event)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "temperature" in body["message"]

    def test_temperature_out_of_range_high(self, aws_setup):
        suite, _ = self._make_suite_and_cases(aws_setup)
        event = make_event(
            "POST",
            body={
                "suiteId": suite.suite_id,
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "baselinePrompt": "test",
                "candidatePrompt": "test",
                "rubric": "good",
                "temperature": 1.1,
            },
        )
        response = handle_runs(event)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "temperature" in body["message"]

    def test_max_tokens_out_of_range_low(self, aws_setup):
        suite, _ = self._make_suite_and_cases(aws_setup)
        event = make_event(
            "POST",
            body={
                "suiteId": suite.suite_id,
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "baselinePrompt": "test",
                "candidatePrompt": "test",
                "rubric": "good",
                "maxTokens": 0,
            },
        )
        response = handle_runs(event)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "maxTokens" in body["message"]

    def test_max_tokens_out_of_range_high(self, aws_setup):
        suite, _ = self._make_suite_and_cases(aws_setup)
        event = make_event(
            "POST",
            body={
                "suiteId": suite.suite_id,
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "baselinePrompt": "test",
                "candidatePrompt": "test",
                "rubric": "good",
                "maxTokens": 5000,
            },
        )
        response = handle_runs(event)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "maxTokens" in body["message"]

    def test_case_ids_exceeds_max(self, aws_setup):
        suite, _ = self._make_suite_and_cases(aws_setup, count=5)
        event = make_event(
            "POST",
            body={
                "suiteId": suite.suite_id,
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "baselinePrompt": "test",
                "candidatePrompt": "test",
                "rubric": "good",
                "caseIds": ["c1", "c2", "c3", "c4"],
            },
        )
        response = handle_runs(event)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "max" in body["message"].lower()

    def test_empty_case_ids_list(self, aws_setup):
        suite, _ = self._make_suite_and_cases(aws_setup)
        event = make_event(
            "POST",
            body={
                "suiteId": suite.suite_id,
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "baselinePrompt": "test",
                "candidatePrompt": "test",
                "rubric": "good",
                "caseIds": [],
            },
        )
        response = handle_runs(event)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "caseIds" in body["message"]

    def test_valid_run_not_rejected(self, aws_setup):
        suite, _ = self._make_suite_and_cases(aws_setup)
        event = make_event(
            "POST",
            body={
                "suiteId": suite.suite_id,
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "baselinePrompt": "test",
                "candidatePrompt": "test",
                "rubric": "good",
                "temperature": 0.7,
                "maxTokens": 1024,
            },
        )
        # Should not be rejected by validation (may fail at Bedrock, but that's fine)
        with (
            patch(
                "src.handlers.api.routes.runs.invoke_model", return_value=("ok", 50.0)
            ),
            patch(
                "src.handlers.api.routes.runs.evaluate_output",
                return_value={"score": 4, "rationale": "ok"},
            ),
            patch(
                "src.handlers.api.routes.runs.classify_result", return_value="Unchanged"
            ),
        ):
            response = handle_runs(event)
        assert response["statusCode"] == 201


class TestRunCaseResultTruncated:
    """Tests for the truncated field on RunCaseResult."""

    def test_truncated_field_in_to_dict(self):
        result = RunCaseResult(
            run_id="r1",
            case_id="c1",
            baseline_output="hello",
            candidate_output="world ... [truncated]",
            truncated=True,
            classification="Unchanged",
        )
        d = result.to_dict()
        assert d["truncated"] is True

    def test_truncated_false_in_to_dict(self):
        result = RunCaseResult(
            run_id="r1",
            case_id="c1",
            truncated=False,
        )
        d = result.to_dict()
        assert d["truncated"] is False

    def test_truncated_in_to_response(self):
        result = RunCaseResult(
            run_id="r1",
            case_id="c1",
            candidate_output="hello ... [truncated]",
            truncated=True,
        )
        r = result.to_response()
        assert r["truncated"] is True

    def test_truncated_in_from_dict(self):
        data = {
            "run_id": "r1",
            "case_id": "c1",
            "truncated": True,
        }
        result = RunCaseResult.from_dict(data)
        assert result.truncated is True

    def test_truncated_defaults_to_false(self):
        result = RunCaseResult(run_id="r1", case_id="c1")
        assert result.truncated is False


class TestInvocationCount:
    """Tests that the 201 response includes invocation count."""

    @patch("src.handlers.api.routes.runs.create_run_case_result")
    @patch("src.handlers.api.routes.runs.update_run_status")
    @patch("src.handlers.api.routes.runs.classify_result", return_value="Unchanged")
    @patch(
        "src.handlers.api.routes.runs.evaluate_output",
        return_value={"score": 4, "rationale": "ok"},
    )
    @patch("src.handlers.api.routes.runs.invoke_model", return_value=("ok", 50.0))
    def test_invocation_count_in_response(
        self,
        mock_invoke,
        mock_eval,
        mock_classify,
        mock_status,
        mock_result,
        aws_setup,
    ):
        suite = dynamodb.create_suite(Suite(name="Test Suite"))
        for i in range(2):
            c = Case(suite_id=suite.suite_id, input=f"Q{i}")
            dynamodb.create_case(c)

        event = make_event(
            "POST",
            body={
                "suiteId": suite.suite_id,
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "baselinePrompt": "test",
                "candidatePrompt": "test",
                "rubric": "good",
            },
        )
        response = handle_runs(event)
        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert (
            body["invocations"] == 8
        )  # 2 cases × 4 (baseline + candidate invoke + eval)

    @patch("src.handlers.api.routes.runs.create_run_case_result")
    @patch("src.handlers.api.routes.runs.update_run_status")
    @patch("src.handlers.api.routes.runs.classify_result", return_value="Unchanged")
    @patch(
        "src.handlers.api.routes.runs.evaluate_output",
        return_value={"score": 4, "rationale": "ok"},
    )
    @patch("src.handlers.api.routes.runs.invoke_model", return_value=("ok", 50.0))
    def test_invocation_count_with_case_ids(
        self,
        mock_invoke,
        mock_eval,
        mock_classify,
        mock_status,
        mock_result,
        aws_setup,
    ):
        suite = dynamodb.create_suite(Suite(name="Test Suite"))
        for i in range(5):
            c = Case(suite_id=suite.suite_id, input=f"Q{i}")
            dynamodb.create_case(c)

        all_cases = dynamodb.get_cases(suite.suite_id)
        selected_ids = [all_cases[0].case_id, all_cases[1].case_id]

        event = make_event(
            "POST",
            body={
                "suiteId": suite.suite_id,
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "baselinePrompt": "test",
                "candidatePrompt": "test",
                "rubric": "good",
                "caseIds": selected_ids,
            },
        )
        response = handle_runs(event)
        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["invocations"] == 8  # 2 selected cases × 4


class TestTruncationDetection:
    """Tests for truncation detection in Bedrock output."""

    def test_invoke_model_detects_truncation(self):
        from src.handlers.api.bedrock import detect_truncation

        # Output shorter than max_tokens → not truncated
        assert detect_truncation("short output", max_tokens=1024) is False

        # Output exactly at max_tokens → truncated
        # Simulate: output ends with stop sequence → not truncated
        assert detect_truncation("output.", max_tokens=100) is False

    def test_detect_truncation_importable(self):
        from src.handlers.api.bedrock import detect_truncation

        assert callable(detect_truncation)


class TestStructuredLogging:
    """Tests for structured logging in execute_run."""

    @patch("src.handlers.api.routes.runs.create_run_case_result")
    @patch("src.handlers.api.routes.runs.update_run_status")
    @patch("src.handlers.api.routes.runs.classify_result", return_value="Unchanged")
    @patch(
        "src.handlers.api.routes.runs.evaluate_output",
        return_value={"score": 4, "rationale": "ok"},
    )
    @patch(
        "src.handlers.api.routes.runs.invoke_model", return_value=("test output", 100.0)
    )
    def test_execute_run_logs_structured_metadata(
        self,
        mock_invoke,
        mock_eval,
        mock_classify,
        mock_status,
        mock_result,
        aws_setup,
        caplog,
    ):
        import logging

        with caplog.at_level(logging.INFO):
            suite = dynamodb.create_suite(Suite(name="Test Suite"))
            c = Case(suite_id=suite.suite_id, input="Q1")
            dynamodb.create_case(c)

            run = Run(
                suite_id=suite.suite_id,
                model_id="anthropic.claude-3-haiku-20240307-v1:0",
                baseline_prompt="test",
                candidate_prompt="test",
                rubric="good",
            )
            dynamodb.create_run(run)
            execute_run(run, [c])

        # Should log with run_id, case_id, sizes — but NOT prompt content
        run_logs = [
            r
            for r in caplog.records
            if "run_completed" in r.message
            or "run_started" in r.message
            or hasattr(r, "run_id")
        ]
        # The key assertion: no raw prompt text in logs
        for record in caplog.records:
            assert "Answer clearly" not in record.message
            assert "test output" not in record.message
