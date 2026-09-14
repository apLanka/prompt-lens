"""Run-Case Result data model."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RunCaseResult:
    """The outcome of evaluating a specific Case within a Run."""

    run_id: str
    case_id: str
    baseline_output: Optional[str] = None
    candidate_output: Optional[str] = None
    baseline_score: Optional[int] = None
    candidate_score: Optional[int] = None
    baseline_rationale: Optional[str] = None
    candidate_rationale: Optional[str] = None
    baseline_latency_ms: Optional[float] = None
    candidate_latency_ms: Optional[float] = None
    classification: str = (
        "Needs review"  # Improved, Regressed, Unchanged, Needs review, Failed
    )
    error: Optional[str] = None
    tags: Optional[List[str]] = None
    truncated: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for DynamoDB storage."""
        result = {
            "run_id": self.run_id,
            "case_id": self.case_id,
            "classification": self.classification,
        }
        if self.baseline_output is not None:
            result["baseline_output"] = self.baseline_output
        if self.candidate_output is not None:
            result["candidate_output"] = self.candidate_output
        if self.baseline_score is not None:
            result["baseline_score"] = self.baseline_score
        if self.candidate_score is not None:
            result["candidate_score"] = self.candidate_score
        if self.baseline_rationale is not None:
            result["baseline_rationale"] = self.baseline_rationale
        if self.candidate_rationale is not None:
            result["candidate_rationale"] = self.candidate_rationale
        if self.baseline_latency_ms is not None:
            result["baseline_latency_ms"] = self.baseline_latency_ms
        if self.candidate_latency_ms is not None:
            result["candidate_latency_ms"] = self.candidate_latency_ms
        if self.error is not None:
            result["error"] = self.error
        if self.tags is not None:
            result["tags"] = self.tags
        result["truncated"] = self.truncated
        return result

    def to_response(self) -> dict:
        """Convert to API response format."""
        result = {
            "runId": self.run_id,
            "caseId": self.case_id,
            "classification": self.classification,
        }
        if self.baseline_output is not None:
            result["baselineOutput"] = self.baseline_output
        if self.candidate_output is not None:
            result["candidateOutput"] = self.candidate_output
        if self.baseline_score is not None:
            result["baselineScore"] = self.baseline_score
        if self.candidate_score is not None:
            result["candidateScore"] = self.candidate_score
        if self.baseline_rationale is not None:
            result["baselineRationale"] = self.baseline_rationale
        if self.candidate_rationale is not None:
            result["candidateRationale"] = self.candidate_rationale
        if self.baseline_latency_ms is not None:
            result["baselineLatencyMs"] = self.baseline_latency_ms
        if self.candidate_latency_ms is not None:
            result["candidateLatencyMs"] = self.candidate_latency_ms
        if self.error is not None:
            result["error"] = self.error
        if self.tags is not None:
            result["tags"] = self.tags
        result["truncated"] = self.truncated
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "RunCaseResult":
        """Create RunCaseResult from DynamoDB item."""
        return cls(
            run_id=data["run_id"],
            case_id=data["case_id"],
            baseline_output=data.get("baseline_output"),
            candidate_output=data.get("candidate_output"),
            baseline_score=data.get("baseline_score"),
            candidate_score=data.get("candidate_score"),
            baseline_rationale=data.get("baseline_rationale"),
            candidate_rationale=data.get("candidate_rationale"),
            baseline_latency_ms=data.get("baseline_latency_ms"),
            candidate_latency_ms=data.get("candidate_latency_ms"),
            classification=data.get("classification", "Needs review"),
            error=data.get("error"),
            tags=data.get("tags"),
            truncated=data.get("truncated", False),
        )
