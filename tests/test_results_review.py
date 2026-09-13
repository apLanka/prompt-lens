"""Tests for Results & Review features."""

import json
import pytest
from src.handlers.api.models import Run, RunCaseResult
from src.handlers.api.dynamodb import (
    create_run,
    create_run_case_result,
)


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
        classifications = ["Improved", "Regressed", "Unchanged", "Needs review"]
        scores = [4, 2, 3, 3]
        for i, (classification, score) in enumerate(zip(classifications, scores)):
            result = RunCaseResult(
                run_id=created_run.run_id,
                case_id=f"case-{i}",
                baseline_output=f"Baseline output {i}",
                candidate_output=f"Candidate output {i}",
                baseline_score=3,
                candidate_score=score,
                baseline_rationale="Baseline rationale",
                candidate_rationale="Candidate rationale",
                baseline_latency_ms=100,
                candidate_latency_ms=120,
                classification=classification,
            )
            create_run_case_result(result)

        from src.handlers.api.routes.runs import get_run_handler

        response = get_run_handler(created_run.run_id)
        body = json.loads(response["body"])

        assert "summary" in body
        assert body["summary"]["total"] == 4
        assert body["summary"]["improved"] == 1
        assert body["summary"]["regressed"] == 1
        assert body["summary"]["unchanged"] == 1
        assert body["summary"]["needsReview"] == 1
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

    def test_run_response_summary_empty_results(self, aws_setup):
        """Summary should return all zeros when no results exist."""
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="Baseline prompt",
            candidate_prompt="Candidate prompt",
            rubric="Test rubric",
        )
        created_run = create_run(run)

        from src.handlers.api.routes.runs import get_run_handler

        response = get_run_handler(created_run.run_id)
        body = json.loads(response["body"])

        assert body["summary"]["total"] == 0
        assert body["summary"]["improved"] == 0
        assert body["summary"]["regressed"] == 0
        assert body["summary"]["unchanged"] == 0
        assert body["summary"]["needsReview"] == 0
        assert body["summary"]["failed"] == 0


class TestListRunsFiltering:
    """Test filtering in list_runs."""

    def test_list_runs_filter_by_status(self, aws_setup):
        """Should filter runs by status."""
        for i, status in enumerate(["COMPLETED", "FAILED", "COMPLETED"]):
            run = Run(
                suite_id="suite-1",
                model_id="anthropic.claude-3-sonnet",
                baseline_prompt="Baseline",
                candidate_prompt="Candidate",
                rubric="Rubric",
            )
            run.status = status
            if status in ["COMPLETED", "FAILED"]:
                run.completed_at = "2026-09-13T10:00:00Z"
            create_run(run)

        from src.handlers.api.routes.runs import list_runs_handler
        from unittest.mock import patch

        with patch(
            "src.handlers.api.routes.runs.get_query_params",
            return_value={"status": "COMPLETED"},
        ):
            response = list_runs_handler()
            body = json.loads(response["body"])
            assert len(body) == 2
            assert all(r["status"] == "COMPLETED" for r in body)

    def test_list_runs_filter_by_suite(self, aws_setup):
        """Should filter runs by suite_id."""
        for suite_id in ["suite-1", "suite-2", "suite-1"]:
            run = Run(
                suite_id=suite_id,
                model_id="anthropic.claude-3-sonnet",
                baseline_prompt="Baseline",
                candidate_prompt="Candidate",
                rubric="Rubric",
            )
            create_run(run)

        from src.handlers.api.routes.runs import list_runs_handler
        from unittest.mock import patch

        with patch(
            "src.handlers.api.routes.runs.get_query_params",
            return_value={"suiteId": "suite-1"},
        ):
            response = list_runs_handler()
            body = json.loads(response["body"])
            assert len(body) == 2
            assert all(r["suiteId"] == "suite-1" for r in body)

    def test_list_runs_with_real_event_filters_by_status(self, aws_setup):
        """Integration test: event passthrough extracts filters from queryStringParameters."""
        for status in ["COMPLETED", "FAILED", "COMPLETED"]:
            run = Run(
                suite_id="suite-1",
                model_id="anthropic.claude-3-sonnet",
                baseline_prompt="Baseline",
                candidate_prompt="Candidate",
                rubric="Rubric",
            )
            run.status = status
            if status in ["COMPLETED", "FAILED"]:
                run.completed_at = "2026-09-13T10:00:00Z"
            create_run(run)

        from src.handlers.api.routes.runs import list_runs_handler

        event = {
            "httpMethod": "GET",
            "queryStringParameters": {"status": "COMPLETED"},
        }
        response = list_runs_handler(event)
        body = json.loads(response["body"])
        assert len(body) == 2
        assert all(r["status"] == "COMPLETED" for r in body)

    def test_list_runs_with_real_event_filters_by_suite(self, aws_setup):
        """Integration test: event passthrough extracts suiteId from queryStringParameters."""
        for suite_id in ["suite-1", "suite-2", "suite-1"]:
            run = Run(
                suite_id=suite_id,
                model_id="anthropic.claude-3-sonnet",
                baseline_prompt="Baseline",
                candidate_prompt="Candidate",
                rubric="Rubric",
            )
            create_run(run)

        from src.handlers.api.routes.runs import list_runs_handler

        event = {
            "httpMethod": "GET",
            "queryStringParameters": {"suiteId": "suite-1"},
        }
        response = list_runs_handler(event)
        body = json.loads(response["body"])
        assert len(body) == 2
        assert all(r["suiteId"] == "suite-1" for r in body)
