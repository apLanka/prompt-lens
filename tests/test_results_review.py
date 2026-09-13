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
