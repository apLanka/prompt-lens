"""Case data model."""

from dataclasses import dataclass, field
from typing import List, Optional
import uuid


@dataclass
class Case:
    """An individual test case within a Suite."""

    suite_id: str
    input: str
    case_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    expected_behavior: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for DynamoDB storage."""
        result = {
            "case_id": self.case_id,
            "suite_id": self.suite_id,
            "input": self.input,
        }
        if self.expected_behavior:
            result["expected_behavior"] = self.expected_behavior
        if self.tags:
            result["tags"] = self.tags
        return result

    def to_response(self) -> dict:
        """Convert to API response format."""
        result = {
            "caseId": self.case_id,
            "suiteId": self.suite_id,
            "input": self.input,
        }
        if self.expected_behavior:
            result["expectedBehavior"] = self.expected_behavior
        if self.tags:
            result["tags"] = self.tags
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Case":
        """Create Case from DynamoDB item."""
        return cls(
            case_id=data["case_id"],
            suite_id=data["suite_id"],
            input=data["input"],
            expected_behavior=data.get("expected_behavior"),
            tags=data.get("tags", []),
        )
