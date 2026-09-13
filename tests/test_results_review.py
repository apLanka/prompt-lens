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


class TestCaseResultFiltering:
    """Test filtering in get_run_case_results."""

    def test_filter_cases_by_classification(self, aws_setup):
        """Should filter case results by classification."""
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="Baseline",
            candidate_prompt="Candidate",
            rubric="Rubric",
        )
        created_run = create_run(run)

        # Create results with different classifications
        for i, classification in enumerate(["Improved", "Regressed", "Improved"]):
            result = RunCaseResult(
                run_id=created_run.run_id,
                case_id=f"case-{i}",
                baseline_output=f"Output {i}",
                candidate_output=f"Candidate {i}",
                baseline_score=3,
                candidate_score=4 if classification == "Improved" else 2,
                baseline_rationale="Rationale",
                candidate_rationale="Rationale",
                baseline_latency_ms=100,
                candidate_latency_ms=120,
                classification=classification,
            )
            create_run_case_result(result)

        from src.handlers.api.dynamodb import get_run_case_results

        results = get_run_case_results(created_run.run_id, classification="Improved")
        assert len(results) == 2
        assert all(r.classification == "Improved" for r in results)

    def test_filter_cases_by_failed(self, aws_setup):
        """Should return only Failed results when filtering by Failed."""
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="Baseline",
            candidate_prompt="Candidate",
            rubric="Rubric",
        )
        created_run = create_run(run)

        # Create mixed results
        result_ok = RunCaseResult(
            run_id=created_run.run_id,
            case_id="case-0",
            baseline_output="Output",
            candidate_output="Candidate",
            baseline_score=3,
            candidate_score=4,
            baseline_rationale="Rationale",
            candidate_rationale="Rationale",
            baseline_latency_ms=100,
            candidate_latency_ms=120,
            classification="Improved",
        )
        create_run_case_result(result_ok)

        result_failed = RunCaseResult(
            run_id=created_run.run_id,
            case_id="case-1",
            error="Timeout",
            classification="Failed",
        )
        create_run_case_result(result_failed)

        from src.handlers.api.dynamodb import get_run_case_results

        results = get_run_case_results(created_run.run_id, classification="Failed")
        assert len(results) == 1
        assert results[0].classification == "Failed"


class TestTagFiltering:
    """Test filtering by tags."""

    def test_filter_cases_by_tag(self, aws_setup):
        """Should filter case results by tag."""
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="Baseline",
            candidate_prompt="Candidate",
            rubric="Rubric",
        )
        created_run = create_run(run)

        # Create results with different tags
        result1 = RunCaseResult(
            run_id=created_run.run_id,
            case_id="case-0",
            baseline_output="Output 0",
            candidate_output="Candidate 0",
            baseline_score=3,
            candidate_score=4,
            baseline_rationale="Rationale",
            candidate_rationale="Rationale",
            baseline_latency_ms=100,
            candidate_latency_ms=120,
            classification="Improved",
            tags=["critical", "regression"],
        )
        create_run_case_result(result1)

        result2 = RunCaseResult(
            run_id=created_run.run_id,
            case_id="case-1",
            baseline_output="Output 1",
            candidate_output="Candidate 1",
            baseline_score=3,
            candidate_score=3,
            baseline_rationale="Rationale",
            candidate_rationale="Rationale",
            baseline_latency_ms=100,
            candidate_latency_ms=120,
            classification="Unchanged",
            tags=["performance"],
        )
        create_run_case_result(result2)

        from src.handlers.api.dynamodb import get_run_case_results

        results = get_run_case_results(created_run.run_id, tags=["critical"])
        assert len(results) == 1
        assert results[0].case_id == "case-0"


class TestFilteredEndpoints:
    """Test filtered API endpoints."""

    def test_get_run_with_classification_filter(self, aws_setup):
        """GET /runs/{runId}?classification=Improved should return only improved results."""
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="Baseline",
            candidate_prompt="Candidate",
            rubric="Rubric",
        )
        created_run = create_run(run)

        # Create mixed results
        for i, classification in enumerate(["Improved", "Regressed"]):
            result = RunCaseResult(
                run_id=created_run.run_id,
                case_id=f"case-{i}",
                baseline_output=f"Output {i}",
                candidate_output=f"Candidate {i}",
                baseline_score=3,
                candidate_score=4 if classification == "Improved" else 2,
                baseline_rationale="Rationale",
                candidate_rationale="Rationale",
                baseline_latency_ms=100,
                candidate_latency_ms=120,
                classification=classification,
            )
            create_run_case_result(result)

        from src.handlers.api.routes.runs import handle_run_by_id

        event = {
            "httpMethod": "GET",
            "pathParameters": {"runId": created_run.run_id},
            "queryStringParameters": {"classification": "Improved"},
        }
        response = handle_run_by_id(event)
        body = json.loads(response["body"])

        assert len(body["results"]) == 1
        assert body["results"][0]["classification"] == "Improved"
        # Summary should reflect filtered results
        assert body["summary"]["improved"] == 1
        assert body["summary"]["regressed"] == 0

    def test_get_run_with_tags_filter(self, aws_setup):
        """GET /runs/{runId}?tags=critical,regression returns results matching any tag."""
        run = Run(
            suite_id="suite-1",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="Baseline",
            candidate_prompt="Candidate",
            rubric="Rubric",
        )
        created_run = create_run(run)

        # Create results with different tags
        tagged = [
            (["critical", "regression"], "Improved"),
            (["performance"], "Regressed"),
            (None, "Unchanged"),
        ]
        for i, (tags, classification) in enumerate(tagged):
            result = RunCaseResult(
                run_id=created_run.run_id,
                case_id=f"case-{i}",
                baseline_output=f"Output {i}",
                candidate_output=f"Candidate {i}",
                baseline_score=3,
                candidate_score=4 if classification == "Improved" else 3,
                baseline_rationale="Rationale",
                candidate_rationale="Rationale",
                baseline_latency_ms=100,
                candidate_latency_ms=120,
                classification=classification,
                tags=tags,
            )
            create_run_case_result(result)

        from src.handlers.api.routes.runs import handle_run_by_id

        event = {
            "httpMethod": "GET",
            "pathParameters": {"runId": created_run.run_id},
            "queryStringParameters": {"tags": "critical,regression"},
        }
        response = handle_run_by_id(event)
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert len(body["results"]) == 1
        assert body["results"][0]["caseId"] == "case-0"
        assert body["results"][0]["tags"] == ["critical", "regression"]
        # Summary is computed on filtered results
        assert body["summary"]["total"] == 1
        assert body["summary"]["improved"] == 1

    def test_list_runs_with_status_filter(self, aws_setup):
        """GET /runs?status=COMPLETED should return only completed runs."""
        for i, status in enumerate(["COMPLETED", "FAILED"]):
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

        from src.handlers.api.routes.runs import handle_runs

        event = {
            "httpMethod": "GET",
            "queryStringParameters": {"status": "COMPLETED"},
        }
        response = handle_runs(event)
        body = json.loads(response["body"])

        assert len(body) == 1
        assert body[0]["status"] == "COMPLETED"
