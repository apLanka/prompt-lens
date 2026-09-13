"""Tests for data models."""

import pytest
from datetime import datetime, timezone

from src.handlers.api.models import Run, RunCaseResult


class TestRun:
    def test_create_run(self):
        run = Run(
            suite_id="suite-123",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="You are a helpful assistant.",
            candidate_prompt="You are a helpful assistant. Be concise.",
            rubric="Evaluate the quality of the response.",
        )
        assert run.suite_id == "suite-123"
        assert run.model_id == "anthropic.claude-3-sonnet"
        assert run.baseline_prompt == "You are a helpful assistant."
        assert run.candidate_prompt == "You are a helpful assistant. Be concise."
        assert run.rubric == "Evaluate the quality of the response."
        assert run.status == "RUNNING"
        assert run.temperature == 0.7
        assert run.max_tokens == 1024
        assert run.completed_at is None

    def test_run_defaults(self):
        run = Run(
            suite_id="suite-123",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="prompt",
            candidate_prompt="prompt",
            rubric="rubric",
        )
        assert run.run_id is not None
        assert len(run.run_id) > 0
        assert run.created_at is not None
        assert run.status == "RUNNING"
        assert run.temperature == 0.7
        assert run.max_tokens == 1024
        assert run.completed_at is None

    def test_run_to_dict(self):
        run = Run(
            suite_id="suite-123",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="prompt",
            candidate_prompt="prompt",
            rubric="rubric",
            run_id="run-123",
            created_at="2024-01-01T00:00:00Z",
        )
        result = run.to_dict()
        assert result["run_id"] == "run-123"
        assert result["suite_id"] == "suite-123"
        assert result["model_id"] == "anthropic.claude-3-sonnet"
        assert result["baseline_prompt"] == "prompt"
        assert result["candidate_prompt"] == "prompt"
        assert result["rubric"] == "rubric"
        assert result["status"] == "RUNNING"
        assert result["temperature"] == 0.7
        assert result["max_tokens"] == 1024
        assert result["created_at"] == "2024-01-01T00:00:00Z"
        assert "completed_at" not in result

    def test_run_to_dict_with_completed_at(self):
        run = Run(
            suite_id="suite-123",
            model_id="model",
            baseline_prompt="p",
            candidate_prompt="p",
            rubric="r",
            completed_at="2024-01-01T01:00:00Z",
        )
        result = run.to_dict()
        assert result["completed_at"] == "2024-01-01T01:00:00Z"

    def test_run_to_response(self):
        run = Run(
            suite_id="suite-123",
            model_id="anthropic.claude-3-sonnet",
            baseline_prompt="prompt",
            candidate_prompt="prompt",
            rubric="rubric",
            run_id="run-123",
            created_at="2024-01-01T00:00:00Z",
        )
        result = run.to_response()
        assert result["runId"] == "run-123"
        assert result["suiteId"] == "suite-123"
        assert result["modelId"] == "anthropic.claude-3-sonnet"
        assert result["baselinePrompt"] == "prompt"
        assert result["candidatePrompt"] == "prompt"
        assert result["rubric"] == "rubric"
        assert result["status"] == "RUNNING"
        assert result["temperature"] == 0.7
        assert result["maxTokens"] == 1024
        assert result["createdAt"] == "2024-01-01T00:00:00Z"
        assert "completedAt" not in result

    def test_run_to_response_with_completed_at(self):
        run = Run(
            suite_id="suite-123",
            model_id="model",
            baseline_prompt="p",
            candidate_prompt="p",
            rubric="r",
            completed_at="2024-01-01T01:00:00Z",
        )
        result = run.to_response()
        assert result["completedAt"] == "2024-01-01T01:00:00Z"

    def test_run_from_dict(self):
        data = {
            "run_id": "run-123",
            "suite_id": "suite-123",
            "model_id": "anthropic.claude-3-sonnet",
            "baseline_prompt": "prompt",
            "candidate_prompt": "prompt",
            "rubric": "rubric",
            "status": "COMPLETED",
            "temperature": 0.5,
            "max_tokens": 2048,
            "created_at": "2024-01-01T00:00:00Z",
            "completed_at": "2024-01-01T01:00:00Z",
        }
        run = Run.from_dict(data)
        assert run.run_id == "run-123"
        assert run.suite_id == "suite-123"
        assert run.model_id == "anthropic.claude-3-sonnet"
        assert run.baseline_prompt == "prompt"
        assert run.candidate_prompt == "prompt"
        assert run.rubric == "rubric"
        assert run.status == "COMPLETED"
        assert run.temperature == 0.5
        assert run.max_tokens == 2048
        assert run.created_at == "2024-01-01T00:00:00Z"
        assert run.completed_at == "2024-01-01T01:00:00Z"

    def test_run_from_dict_defaults(self):
        data = {
            "run_id": "run-123",
            "suite_id": "suite-123",
            "model_id": "model",
            "baseline_prompt": "prompt",
            "candidate_prompt": "prompt",
            "rubric": "rubric",
            "created_at": "2024-01-01T00:00:00Z",
        }
        run = Run.from_dict(data)
        assert run.status == "RUNNING"
        assert run.temperature == 0.7
        assert run.max_tokens == 1024
        assert run.completed_at is None


class TestRunCaseResult:
    def test_create_run_case_result(self):
        result = RunCaseResult(
            run_id="run-123",
            case_id="case-456",
        )
        assert result.run_id == "run-123"
        assert result.case_id == "case-456"
        assert result.classification == "Needs review"
        assert result.baseline_output is None
        assert result.candidate_output is None
        assert result.baseline_score is None
        assert result.candidate_score is None
        assert result.baseline_rationale is None
        assert result.candidate_rationale is None
        assert result.baseline_latency_ms is None
        assert result.candidate_latency_ms is None
        assert result.error is None

    def test_run_case_result_to_dict(self):
        result = RunCaseResult(
            run_id="run-123",
            case_id="case-456",
            baseline_output="baseline output",
            candidate_output="candidate output",
            baseline_score=4,
            candidate_score=5,
            baseline_rationale="Good response",
            candidate_rationale="Excellent response",
            baseline_latency_ms=100.0,
            candidate_latency_ms=150.0,
            classification="Improved",
        )
        d = result.to_dict()
        assert d["run_id"] == "run-123"
        assert d["case_id"] == "case-456"
        assert d["baseline_output"] == "baseline output"
        assert d["candidate_output"] == "candidate output"
        assert d["baseline_score"] == 4
        assert d["candidate_score"] == 5
        assert d["baseline_rationale"] == "Good response"
        assert d["candidate_rationale"] == "Excellent response"
        assert d["baseline_latency_ms"] == 100.0
        assert d["candidate_latency_ms"] == 150.0
        assert d["classification"] == "Improved"

    def test_run_case_result_to_dict_optional_none(self):
        result = RunCaseResult(
            run_id="run-123",
            case_id="case-456",
        )
        d = result.to_dict()
        assert "baseline_output" not in d
        assert "candidate_output" not in d
        assert "baseline_score" not in d
        assert "candidate_score" not in d
        assert "baseline_rationale" not in d
        assert "candidate_rationale" not in d
        assert "baseline_latency_ms" not in d
        assert "candidate_latency_ms" not in d
        assert "error" not in d

    def test_run_case_result_to_dict_with_error(self):
        result = RunCaseResult(
            run_id="run-123",
            case_id="case-456",
            error="Timeout error",
            classification="Failed",
        )
        d = result.to_dict()
        assert d["error"] == "Timeout error"
        assert d["classification"] == "Failed"

    def test_run_case_result_to_response(self):
        result = RunCaseResult(
            run_id="run-123",
            case_id="case-456",
            baseline_output="baseline output",
            candidate_output="candidate output",
            baseline_score=4,
            candidate_score=5,
            baseline_rationale="Good response",
            candidate_rationale="Excellent response",
            baseline_latency_ms=100.0,
            candidate_latency_ms=150.0,
            classification="Improved",
        )
        d = result.to_response()
        assert d["runId"] == "run-123"
        assert d["caseId"] == "case-456"
        assert d["baselineOutput"] == "baseline output"
        assert d["candidateOutput"] == "candidate output"
        assert d["baselineScore"] == 4
        assert d["candidateScore"] == 5
        assert d["baselineRationale"] == "Good response"
        assert d["candidateRationale"] == "Excellent response"
        assert d["baselineLatencyMs"] == 100.0
        assert d["candidateLatencyMs"] == 150.0
        assert d["classification"] == "Improved"

    def test_run_case_result_to_response_optional_none(self):
        result = RunCaseResult(
            run_id="run-123",
            case_id="case-456",
        )
        d = result.to_response()
        assert "baselineOutput" not in d
        assert "candidateOutput" not in d
        assert "baselineScore" not in d
        assert "candidateScore" not in d
        assert "baselineRationale" not in d
        assert "candidateRationale" not in d
        assert "baselineLatencyMs" not in d
        assert "candidateLatencyMs" not in d
        assert "error" not in d

    def test_run_case_result_to_response_with_error(self):
        result = RunCaseResult(
            run_id="run-123",
            case_id="case-456",
            error="Timeout error",
            classification="Failed",
        )
        d = result.to_response()
        assert d["error"] == "Timeout error"
        assert d["classification"] == "Failed"

    def test_run_case_result_from_dict(self):
        data = {
            "run_id": "run-123",
            "case_id": "case-456",
            "baseline_output": "baseline output",
            "candidate_output": "candidate output",
            "baseline_score": 4,
            "candidate_score": 5,
            "baseline_rationale": "Good response",
            "candidate_rationale": "Excellent response",
            "baseline_latency_ms": 100.0,
            "candidate_latency_ms": 150.0,
            "classification": "Improved",
            "error": None,
        }
        result = RunCaseResult.from_dict(data)
        assert result.run_id == "run-123"
        assert result.case_id == "case-456"
        assert result.baseline_output == "baseline output"
        assert result.candidate_output == "candidate output"
        assert result.baseline_score == 4
        assert result.candidate_score == 5
        assert result.baseline_rationale == "Good response"
        assert result.candidate_rationale == "Excellent response"
        assert result.baseline_latency_ms == 100.0
        assert result.candidate_latency_ms == 150.0
        assert result.classification == "Improved"
        assert result.error is None

    def test_run_case_result_from_dict_defaults(self):
        data = {
            "run_id": "run-123",
            "case_id": "case-456",
        }
        result = RunCaseResult.from_dict(data)
        assert result.run_id == "run-123"
        assert result.case_id == "case-456"
        assert result.baseline_output is None
        assert result.candidate_output is None
        assert result.baseline_score is None
        assert result.candidate_score is None
        assert result.baseline_rationale is None
        assert result.candidate_rationale is None
        assert result.baseline_latency_ms is None
        assert result.candidate_latency_ms is None
        assert result.classification == "Needs review"
        assert result.error is None

    def test_run_case_result_from_dict_with_error(self):
        data = {
            "run_id": "run-123",
            "case_id": "case-456",
            "error": "Timeout error",
            "classification": "Failed",
        }
        result = RunCaseResult.from_dict(data)
        assert result.error == "Timeout error"
        assert result.classification == "Failed"
