"""Suite data model."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
import uuid


@dataclass
class Suite:
    """A named collection of test cases."""

    name: str
    suite_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    cases: List["Case"] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for DynamoDB storage."""
        return {
            "suite_id": self.suite_id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_response(self) -> dict:
        """Convert to API response format."""
        return {
            "suiteId": self.suite_id,
            "name": self.name,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "caseCount": len(self.cases),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Suite":
        """Create Suite from DynamoDB item."""
        return cls(
            suite_id=data["suite_id"],
            name=data["name"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
