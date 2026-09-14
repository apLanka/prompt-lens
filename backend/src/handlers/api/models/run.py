"""Run data model."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass
class Run:
    """A comparison execution that tests baseline and candidate prompts against selected cases."""

    suite_id: str
    model_id: str
    baseline_prompt: str
    candidate_prompt: str
    rubric: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "RUNNING"  # RUNNING, COMPLETED, PARTIAL, FAILED
    temperature: float = 0.7
    max_tokens: int = 1024
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for DynamoDB storage."""
        result = {
            "run_id": self.run_id,
            "suite_id": self.suite_id,
            "model_id": self.model_id,
            "baseline_prompt": self.baseline_prompt,
            "candidate_prompt": self.candidate_prompt,
            "rubric": self.rubric,
            "status": self.status,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "created_at": self.created_at,
        }
        if self.completed_at:
            result["completed_at"] = self.completed_at
        return result

    def to_response(self) -> dict:
        """Convert to API response format."""
        result = {
            "runId": self.run_id,
            "suiteId": self.suite_id,
            "modelId": self.model_id,
            "baselinePrompt": self.baseline_prompt,
            "candidatePrompt": self.candidate_prompt,
            "rubric": self.rubric,
            "status": self.status,
            "temperature": self.temperature,
            "maxTokens": self.max_tokens,
            "createdAt": self.created_at,
        }
        if self.completed_at:
            result["completedAt"] = self.completed_at
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Run":
        """Create Run from DynamoDB item."""
        return cls(
            run_id=data["run_id"],
            suite_id=data["suite_id"],
            model_id=data["model_id"],
            baseline_prompt=data["baseline_prompt"],
            candidate_prompt=data["candidate_prompt"],
            rubric=data["rubric"],
            status=data.get("status", "RUNNING"),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 1024),
            created_at=data["created_at"],
            completed_at=data.get("completed_at"),
        )
