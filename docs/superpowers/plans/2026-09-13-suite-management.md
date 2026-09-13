# Suite Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement CRUD operations for test Suites and their Cases, including DynamoDB operations, API endpoints, and seed data for a demo suite.

**Architecture:** Extend the Lambda handler with route-based request handling for Suite and Case operations. Use DynamoDB single-table design with PK/SK pattern for efficient queries. Each operation validates input and returns structured JSON responses.

**Tech Stack:** Python 3.11, boto3 (DynamoDB), AWS Lambda, API Gateway

**Spec:** [Feature 2 Ticket](../../.scratch/wayfinder/tickets/02-suite-management.md)

## Global Constraints

- DynamoDB table name: PromptLens
- Suite PK = `SUITE#{suiteId}`, SK = `META`
- Case PK = `SUITE#{suiteId}`, SK = `CASE#{caseId}`
- Case IDs are generated (UUID4)
- Suite IDs are generated (UUID4)
- Timestamps use ISO 8601 format
- All responses include CORS headers
- Input validation required for all operations

---

## File Structure

```
prompt-lens/
├── src/
│   └── handlers/
│       └── api/
│           ├── __init__.py          # Main handler (modify)
│           ├── routes/
│           │   ├── __init__.py      # Route dispatcher (create)
│           │   ├── suites.py        # Suite CRUD operations (create)
│           │   └── cases.py         # Case CRUD operations (create)
│           └── models/
│               ├── __init__.py      # Models package (create)
│               ├── suite.py         # Suite data model (create)
│               └── case.py          # Case data model (create)
├── tests/
│   └── handlers/
│       └── api/
│           ├── __init__.py          # Test package (create)
│           ├── test_suites.py       # Suite tests (create)
│           └── test_cases.py        # Case tests (create)
└── template.yaml                    # No changes needed
```

---

## Task 1: Create Data Models

**Files:**
- Create: `src/handlers/api/models/__init__.py`
- Create: `src/handlers/api/models/suite.py`
- Create: `src/handlers/api/models/case.py`

**Interfaces:**
- Consumes: None (initial models)
- Produces: Suite and Case dataclasses for use by routes

- [ ] **Step 1: Create models package init**

Create `src/handlers/api/models/__init__.py`:

```python
"""Data models for PromptLens API."""

from .suite import Suite
from .case import Case

__all__ = ["Suite", "Case"]
```

- [ ] **Step 2: Create Suite model**

Create `src/handlers/api/models/suite.py`:

```python
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
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cases: List['Case'] = field(default_factory=list)
    
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
    def from_dict(cls, data: dict) -> 'Suite':
        """Create Suite from DynamoDB item."""
        return cls(
            suite_id=data["suite_id"],
            name=data["name"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
```

- [ ] **Step 3: Create Case model**

Create `src/handlers/api/models/case.py`:

```python
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
    def from_dict(cls, data: dict) -> 'Case':
        """Create Case from DynamoDB item."""
        return cls(
            case_id=data["case_id"],
            suite_id=data["suite_id"],
            input=data["input"],
            expected_behavior=data.get("expected_behavior"),
            tags=data.get("tags", []),
        )
```

- [ ] **Step 4: Commit**

```bash
git add src/handlers/api/models/
git commit -m "feat: add Suite and Case data models"
```

---

## Task 2: Create DynamoDB Operations

**Files:**
- Create: `src/handlers/api/dynamodb.py`

**Interfaces:**
- Consumes: Suite, Case models
- Produces: DynamoDB operations for CRUD

- [ ] **Step 1: Create DynamoDB operations module**

Create `src/handlers/api/dynamodb.py`:

```python
"""DynamoDB operations for Suite and Case management."""

import os
from typing import List, Optional
import boto3
from boto3.dynamodb.conditions import Key

from .models import Suite, Case


def get_table():
    """Get DynamoDB table resource."""
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(os.environ.get("TABLE_NAME", "PromptLens"))


def create_suite(suite: Suite) -> Suite:
    """Create a new suite in DynamoDB."""
    table = get_table()
    
    # Create suite metadata
    table.put_item(
        Item={
            "PK": f"SUITE#{suite.suite_id}",
            "SK": "META",
            "suite_id": suite.suite_id,
            "name": suite.name,
            "created_at": suite.created_at,
            "updated_at": suite.updated_at,
        }
    )
    
    return suite


def get_suite(suite_id: str) -> Optional[Suite]:
    """Get a suite by ID."""
    table = get_table()
    
    response = table.get_item(
        Key={
            "PK": f"SUITE#{suite_id}",
            "SK": "META",
        }
    )
    
    item = response.get("Item")
    if not item:
        return None
    
    return Suite(
        suite_id=item["suite_id"],
        name=item["name"],
        created_at=item["created_at"],
        updated_at=item["updated_at"],
    )


def list_suites() -> List[Suite]:
    """List all suites."""
    table = get_table()
    
    response = table.query(
        IndexName="SK-index",
        KeyConditionExpression=Key("SK").eq("META"),
    )
    
    return [
        Suite(
            suite_id=item["suite_id"],
            name=item["name"],
            created_at=item["created_at"],
            updated_at=item["updated_at"],
        )
        for item in response.get("Items", [])
    ]


def update_suite(suite_id: str, name: str) -> Optional[Suite]:
    """Update suite name."""
    table = get_table()
    
    from datetime import datetime, timezone
    updated_at = datetime.now(timezone.utc).isoformat()
    
    response = table.update_item(
        Key={
            "PK": f"SUITE#{suite_id}",
            "SK": "META",
        },
        UpdateExpression="SET #name = :name, updated_at = :updated_at",
        ExpressionAttributeNames={"#name": "name"},
        ExpressionAttributeValues={
            ":name": name,
            ":updated_at": updated_at,
        },
        ReturnValues="ALL_NEW",
    )
    
    attributes = response.get("Attributes", {})
    return Suite(
        suite_id=attributes["suite_id"],
        name=attributes["name"],
        created_at=attributes["created_at"],
        updated_at=attributes["updated_at"],
    )


def delete_suite(suite_id: str) -> bool:
    """Delete suite and all its cases."""
    table = get_table()
    
    # First, get all cases in the suite
    response = table.query(
        KeyConditionExpression=Key("PK").eq(f"SUITE#{suite_id}"),
    )
    
    # Delete suite metadata and all cases
    with table.batch_writer() as batch:
        for item in response.get("Items", []):
            batch.delete_item(
                Key={
                    "PK": item["PK"],
                    "SK": item["SK"],
                }
            )
    
    return True


def create_case(case: Case) -> Case:
    """Create a new case in a suite."""
    table = get_table()
    
    item = {
        "PK": f"SUITE#{case.suite_id}",
        "SK": f"CASE#{case.case_id}",
        "case_id": case.case_id,
        "suite_id": case.suite_id,
        "input": case.input,
    }
    
    if case.expected_behavior:
        item["expected_behavior"] = case.expected_behavior
    
    if case.tags:
        item["tags"] = case.tags
    
    table.put_item(Item=item)
    
    return case


def get_cases(suite_id: str) -> List[Case]:
    """Get all cases for a suite."""
    table = get_table()
    
    response = table.query(
        KeyConditionExpression=Key("PK").eq(f"SUITE#{suite_id}") & Key("SK").begins_with("CASE#"),
    )
    
    return [
        Case(
            case_id=item["case_id"],
            suite_id=item["suite_id"],
            input=item["input"],
            expected_behavior=item.get("expected_behavior"),
            tags=item.get("tags", []),
        )
        for item in response.get("Items", [])
    ]


def get_case(suite_id: str, case_id: str) -> Optional[Case]:
    """Get a specific case."""
    table = get_table()
    
    response = table.get_item(
        Key={
            "PK": f"SUITE#{suite_id}",
            "SK": f"CASE#{case_id}",
        }
    )
    
    item = response.get("Item")
    if not item:
        return None
    
    return Case(
        case_id=item["case_id"],
        suite_id=item["suite_id"],
        input=item["input"],
        expected_behavior=item.get("expected_behavior"),
        tags=item.get("tags", []),
    )


def update_case(suite_id: str, case_id: str, input: str, expected_behavior: str = None, tags: List[str] = None) -> Optional[Case]:
    """Update a case."""
    table = get_table()
    
    update_expr = "SET #input = :input"
    expr_names = {"#input": "input"}
    expr_values = {":input": input}
    
    if expected_behavior is not None:
        update_expr += ", expected_behavior = :expected_behavior"
        expr_values[":expected_behavior"] = expected_behavior
    
    if tags is not None:
        update_expr += ", tags = :tags"
        expr_values[":tags"] = tags
    
    response = table.update_item(
        Key={
            "PK": f"SUITE#{suite_id}",
            "SK": f"CASE#{case_id}",
        },
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
        ReturnValues="ALL_NEW",
    )
    
    attributes = response.get("Attributes", {})
    return Case(
        case_id=attributes["case_id"],
        suite_id=attributes["suite_id"],
        input=attributes["input"],
        expected_behavior=attributes.get("expected_behavior"),
        tags=attributes.get("tags", []),
    )


def delete_case(suite_id: str, case_id: str) -> bool:
    """Delete a case."""
    table = get_table()
    
    table.delete_item(
        Key={
            "PK": f"SUITE#{suite_id}",
            "SK": f"CASE#{case_id}",
        }
    )
    
    return True
```

- [ ] **Step 2: Commit**

```bash
git add src/handlers/api/dynamodb.py
git commit -m "feat: add DynamoDB operations for Suite and Case CRUD"
```

---

## Task 3: Create Route Handlers

**Files:**
- Create: `src/handlers/api/routes/__init__.py`
- Create: `src/handlers/api/routes/suites.py`
- Create: `src/handlers/api/routes/cases.py`

**Interfaces:**
- Consumes: DynamoDB operations
- Produces: Route handlers for API Gateway

- [ ] **Step 1: Create routes package init**

Create `src/handlers/api/routes/__init__.py`:

```python
"""API route handlers."""

from .suites import handle_suites, handle_suite_by_id
from .cases import handle_cases, handle_case_by_id

__all__ = ["handle_suites", "handle_suite_by_id", "handle_cases", "handle_case_by_id"]
```

- [ ] **Step 2: Create Suite route handlers**

Create `src/handlers/api/routes/suites.py`:

```python
"""Suite route handlers."""

import json
from typing import Any, Dict

from ..models import Suite
from ..dynamodb import create_suite, get_suite, list_suites, update_suite, delete_suite, get_cases


def handle_suites(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle /suites routes."""
    method = event.get("httpMethod")
    
    if method == "GET":
        return list_suites_handler()
    elif method == "POST":
        return create_suite_handler(event)
    else:
        return {
            "statusCode": 405,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Method not allowed"}),
        }


def handle_suite_by_id(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle /suites/{suiteId} routes."""
    method = event.get("httpMethod")
    suite_id = event.get("pathParameters", {}).get("suiteId")
    
    if not suite_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "suiteId is required"}),
        }
    
    if method == "GET":
        return get_suite_handler(suite_id)
    elif method == "PATCH":
        return update_suite_handler(event, suite_id)
    elif method == "DELETE":
        return delete_suite_handler(suite_id)
    else:
        return {
            "statusCode": 405,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Method not allowed"}),
        }


def list_suites_handler() -> Dict[str, Any]:
    """List all suites."""
    suites = list_suites()
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps([s.to_response() for s in suites]),
    }


def create_suite_handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new suite."""
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Invalid JSON"}),
        }
    
    name = body.get("name")
    if not name:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "name is required"}),
        }
    
    suite = Suite(name=name)
    created = create_suite(suite)
    
    return {
        "statusCode": 201,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(created.to_response()),
    }


def get_suite_handler(suite_id: str) -> Dict[str, Any]:
    """Get a suite with its cases."""
    suite = get_suite(suite_id)
    if not suite:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Suite not found"}),
        }
    
    cases = get_cases(suite_id)
    response = suite.to_response()
    response["cases"] = [c.to_response() for c in cases]
    
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(response),
    }


def update_suite_handler(event: Dict[str, Any], suite_id: str) -> Dict[str, Any]:
    """Update a suite's name."""
    suite = get_suite(suite_id)
    if not suite:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Suite not found"}),
        }
    
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Invalid JSON"}),
        }
    
    name = body.get("name")
    if not name:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "name is required"}),
        }
    
    updated = update_suite(suite_id, name)
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(updated.to_response()),
    }


def delete_suite_handler(suite_id: str) -> Dict[str, Any]:
    """Delete a suite and all its cases."""
    suite = get_suite(suite_id)
    if not suite:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Suite not found"}),
        }
    
    delete_suite(suite_id)
    return {
        "statusCode": 204,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": "",
    }
```

- [ ] **Step 3: Create Case route handlers**

Create `src/handlers/api/routes/cases.py`:

```python
"""Case route handlers."""

import json
from typing import Any, Dict

from ..models import Case
from ..dynamodb import get_suite, create_case, get_case, update_case, delete_case


def handle_cases(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle /suites/{suiteId}/cases routes."""
    method = event.get("httpMethod")
    suite_id = event.get("pathParameters", {}).get("suiteId")
    
    if not suite_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "suiteId is required"}),
        }
    
    # Verify suite exists
    suite = get_suite(suite_id)
    if not suite:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Suite not found"}),
        }
    
    if method == "POST":
        return create_case_handler(event, suite_id)
    else:
        return {
            "statusCode": 405,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Method not allowed"}),
        }


def handle_case_by_id(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle /suites/{suiteId}/cases/{caseId} routes."""
    method = event.get("httpMethod")
    suite_id = event.get("pathParameters", {}).get("suiteId")
    case_id = event.get("pathParameters", {}).get("caseId")
    
    if not suite_id or not case_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "suiteId and caseId are required"}),
        }
    
    # Verify suite exists
    suite = get_suite(suite_id)
    if not suite:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Suite not found"}),
        }
    
    if method == "PATCH":
        return update_case_handler(event, suite_id, case_id)
    elif method == "DELETE":
        return delete_case_handler(suite_id, case_id)
    else:
        return {
            "statusCode": 405,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Method not allowed"}),
        }


def create_case_handler(event: Dict[str, Any], suite_id: str) -> Dict[str, Any]:
    """Create a new case in a suite."""
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Invalid JSON"}),
        }
    
    input_text = body.get("input")
    if not input_text:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "input is required"}),
        }
    
    case = Case(
        suite_id=suite_id,
        input=input_text,
        expected_behavior=body.get("expectedBehavior"),
        tags=body.get("tags", []),
    )
    
    created = create_case(case)
    
    return {
        "statusCode": 201,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(created.to_response()),
    }


def update_case_handler(event: Dict[str, Any], suite_id: str, case_id: str) -> Dict[str, Any]:
    """Update a case."""
    existing = get_case(suite_id, case_id)
    if not existing:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Case not found"}),
        }
    
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Invalid JSON"}),
        }
    
    input_text = body.get("input")
    if not input_text:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "input is required"}),
        }
    
    updated = update_case(
        suite_id=suite_id,
        case_id=case_id,
        input=input_text,
        expected_behavior=body.get("expectedBehavior"),
        tags=body.get("tags"),
    )
    
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(updated.to_response()),
    }


def delete_case_handler(suite_id: str, case_id: str) -> Dict[str, Any]:
    """Delete a case."""
    existing = get_case(suite_id, case_id)
    if not existing:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Case not found"}),
        }
    
    delete_case(suite_id, case_id)
    return {
        "statusCode": 204,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": "",
    }
```

- [ ] **Step 4: Commit**

```bash
git add src/handlers/api/routes/
git commit -m "feat: add Suite and Case route handlers"
```

---

## Task 4: Update Main Handler with Routing

**Files:**
- Modify: `src/handlers/api/__init__.py`

**Interfaces:**
- Consumes: Route handlers
- Produces: Updated main handler with routing logic

- [ ] **Step 1: Update main handler with routing**

Replace `src/handlers/api/__init__.py` with:

```python
"""PromptLens API Lambda Handler."""

import json
import os
import re
from typing import Any, Dict

from .routes.suites import handle_suites, handle_suite_by_id
from .routes.cases import handle_cases, handle_case_by_id


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for API requests.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    path = event.get("path", "")
    method = event.get("httpMethod", "")
    
    # Health check endpoint
    if path == "/health":
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "status": "healthy",
                    "table": os.environ.get("TABLE_NAME", "PromptLens"),
                }
            ),
        }
    
    # OPTIONS request for CORS
    if method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
            "body": "",
        }
    
    # Route matching
    # /suites/{suiteId}/cases/{caseId}
    case_match = re.match(r"^/suites/([^/]+)/cases/([^/]+)$", path)
    if case_match:
        event["pathParameters"] = {
            "suiteId": case_match.group(1),
            "caseId": case_match.group(2),
        }
        return handle_case_by_id(event)
    
    # /suites/{suiteId}/cases
    cases_match = re.match(r"^/suites/([^/]+)/cases$", path)
    if cases_match:
        event["pathParameters"] = {"suiteId": cases_match.group(1)}
        return handle_cases(event)
    
    # /suites/{suiteId}
    suite_match = re.match(r"^/suites/([^/]+)$", path)
    if suite_match:
        event["pathParameters"] = {"suiteId": suite_match.group(1)}
        return handle_suite_by_id(event)
    
    # /suites
    if path == "/suites":
        return handle_suites(event)
    
    # Default response for unimplemented routes
    return {
        "statusCode": 404,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(
            {
                "message": "Not found",
            }
        ),
    }
```

- [ ] **Step 2: Commit**

```bash
git add src/handlers/api/__init__.py
git commit -m "feat: add routing logic to main handler"
```

---

## Task 5: Create Seed Data

**Files:**
- Create: `src/handlers/api/seed.py`

**Interfaces:**
- Consumes: DynamoDB operations
- Produces: Seed data for demo suite

- [ ] **Step 1: Create seed data module**

Create `src/handlers/api/seed.py`:

```python
"""Seed data for demo suite."""

import os
import boto3
from datetime import datetime, timezone


def seed_demo_suite():
    """Create a demo suite with sample test cases."""
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(os.environ.get("TABLE_NAME", "PromptLens"))
    
    # Demo suite
    suite_id = "demo-support-replies"
    suite_name = "Customer Support Replies"
    now = datetime.now(timezone.utc).isoformat()
    
    # Create suite metadata
    table.put_item(
        Item={
            "PK": f"SUITE#{suite_id}",
            "SK": "META",
            "suite_id": suite_id,
            "name": suite_name,
            "created_at": now,
            "updated_at": now,
        }
    )
    
    # Demo cases
    cases = [
        {
            "case_id": "case-001",
            "input": "I can't access my account. I've tried resetting my password but the email never arrives.",
            "expected_behavior": "Empathize with the user, provide troubleshooting steps for password reset, offer alternative verification methods",
            "tags": ["account-access", "password-reset"],
        },
        {
            "case_id": "case-002",
            "input": "Your product is too expensive. I found a competitor offering similar features for half the price.",
            "expected_behavior": "Acknowledge the concern, highlight unique value propositions, offer to discuss pricing options without being defensive",
            "tags": ["pricing", "competitive"],
        },
        {
            "case_id": "case-003",
            "input": "I've been waiting 3 days for a response to my support ticket. This is unacceptable.",
            "expected_behavior": "Apologize for the delay, explain the reason if known, escalate the issue, provide direct contact information",
            "tags": ["response-time", "escalation"],
        },
    ]
    
    # Create cases
    for case in cases:
        table.put_item(
            Item={
                "PK": f"SUITE#{suite_id}",
                "SK": f"CASE#{case['case_id']}",
                "case_id": case["case_id"],
                "suite_id": suite_id,
                "input": case["input"],
                "expected_behavior": case["expected_behavior"],
                "tags": case["tags"],
            }
        )
    
    print(f"Seeded demo suite '{suite_name}' with {len(cases)} cases")
    return suite_id


if __name__ == "__main__":
    seed_demo_suite()
```

- [ ] **Step 2: Commit**

```bash
git add src/handlers/api/seed.py
git commit -m "feat: add seed data for demo suite"
```

---

## Task 6: Create Tests

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/handlers/__init__.py`
- Create: `tests/handlers/api/__init__.py`
- Create: `tests/handlers/api/test_suites.py`
- Create: `tests/handlers/api/test_cases.py`

**Interfaces:**
- Consumes: All previous modules
- Produces: Test coverage for Suite and Case operations

- [ ] **Step 1: Create test package structure**

Create `tests/__init__.py`:
```python
```

Create `tests/handlers/__init__.py`:
```python
```

Create `tests/handlers/api/__init__.py`:
```python
```

- [ ] **Step 2: Create Suite tests**

Create `tests/handlers/api/test_suites.py`:

```python
"""Tests for Suite operations."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.handlers.api.models import Suite
from src.handlers.api.routes.suites import (
    handle_suites,
    handle_suite_by_id,
    list_suites_handler,
    create_suite_handler,
    get_suite_handler,
    update_suite_handler,
    delete_suite_handler,
)


class TestHandleSuites:
    """Tests for handle_suites router."""
    
    @patch("src.handlers.api.routes.suites.list_suites")
    def test_list_suites(self, mock_list):
        mock_list.return_value = [
            Suite(suite_id="s1", name="Suite 1", created_at="2024-01-01", updated_at="2024-01-01"),
            Suite(suite_id="s2", name="Suite 2", created_at="2024-01-01", updated_at="2024-01-01"),
        ]
        
        event = {"httpMethod": "GET"}
        result = handle_suites(event)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert len(body) == 2
    
    def test_method_not_allowed(self):
        event = {"httpMethod": "DELETE"}
        result = handle_suites(event)
        
        assert result["statusCode"] == 405


class TestCreateSuiteHandler:
    """Tests for create_suite_handler."""
    
    @patch("src.handlers.api.routes.suites.create_suite")
    def test_create_suite_success(self, mock_create):
        mock_create.return_value = Suite(
            suite_id="new-id",
            name="New Suite",
            created_at="2024-01-01",
            updated_at="2024-01-01",
        )
        
        event = {
            "httpMethod": "POST",
            "body": json.dumps({"name": "New Suite"}),
        }
        result = create_suite_handler(event)
        
        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert body["name"] == "New Suite"
    
    def test_create_suite_missing_name(self):
        event = {
            "httpMethod": "POST",
            "body": json.dumps({}),
        }
        result = create_suite_handler(event)
        
        assert result["statusCode"] == 400
    
    def test_create_suite_invalid_json(self):
        event = {
            "httpMethod": "POST",
            "body": "invalid json",
        }
        result = create_suite_handler(event)
        
        assert result["statusCode"] == 400


class TestGetSuiteHandler:
    """Tests for get_suite_handler."""
    
    @patch("src.handlers.api.routes.suites.get_cases")
    @patch("src.handlers.api.routes.suites.get_suite")
    def test_get_suite_success(self, mock_get, mock_cases):
        mock_get.return_value = Suite(
            suite_id="s1",
            name="Suite 1",
            created_at="2024-01-01",
            updated_at="2024-01-01",
        )
        mock_cases.return_value = []
        
        result = get_suite_handler("s1")
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["suiteId"] == "s1"
    
    @patch("src.handlers.api.routes.suites.get_suite")
    def test_get_suite_not_found(self, mock_get):
        mock_get.return_value = None
        
        result = get_suite_handler("nonexistent")
        
        assert result["statusCode"] == 404
```

- [ ] **Step 3: Create Case tests**

Create `tests/handlers/api/test_cases.py`:

```python
"""Tests for Case operations."""

import json
import pytest
from unittest.mock import Mock, patch
from src.handlers.api.models import Case
from src.handlers.api.routes.cases import (
    handle_cases,
    handle_case_by_id,
    create_case_handler,
    update_case_handler,
    delete_case_handler,
)


class TestHandleCases:
    """Tests for handle_cases router."""
    
    @patch("src.handlers.api.routes.cases.get_suite")
    def test_create_case(self, mock_get_suite):
        mock_get_suite.return_value = Mock()
        
        event = {
            "httpMethod": "POST",
            "pathParameters": {"suiteId": "s1"},
            "body": json.dumps({"input": "Test input"}),
        }
        result = handle_cases(event)
        
        assert result["statusCode"] == 201
    
    @patch("src.handlers.api.routes.cases.get_suite")
    def test_suite_not_found(self, mock_get_suite):
        mock_get_suite.return_value = None
        
        event = {
            "httpMethod": "POST",
            "pathParameters": {"suiteId": "nonexistent"},
            "body": json.dumps({"input": "Test input"}),
        }
        result = handle_cases(event)
        
        assert result["statusCode"] == 404


class TestCreateCaseHandler:
    """Tests for create_case_handler."""
    
    @patch("src.handlers.api.routes.cases.create_case")
    def test_create_case_success(self, mock_create):
        mock_create.return_value = Case(
            case_id="c1",
            suite_id="s1",
            input="Test input",
            expected_behavior="Test behavior",
            tags=["test"],
        )
        
        event = {
            "httpMethod": "POST",
            "body": json.dumps({
                "input": "Test input",
                "expectedBehavior": "Test behavior",
                "tags": ["test"],
            }),
        }
        result = create_case_handler(event, "s1")
        
        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert body["input"] == "Test input"
    
    def test_create_case_missing_input(self):
        event = {
            "httpMethod": "POST",
            "body": json.dumps({}),
        }
        result = create_case_handler(event, "s1")
        
        assert result["statusCode"] == 400


class TestDeleteCaseHandler:
    """Tests for delete_case_handler."""
    
    @patch("src.handlers.api.routes.cases.delete_case")
    @patch("src.handlers.api.routes.cases.get_case")
    def test_delete_case_success(self, mock_get, mock_delete):
        mock_get.return_value = Mock()
        mock_delete.return_value = True
        
        result = delete_case_handler("s1", "c1")
        
        assert result["statusCode"] == 204
    
    @patch("src.handlers.api.routes.cases.get_case")
    def test_delete_case_not_found(self, mock_get):
        mock_get.return_value = None
        
        result = delete_case_handler("s1", "nonexistent")
        
        assert result["statusCode"] == 404
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/pasindulanka/LANKA/Development/AWS/prompt-lens
python -m pytest tests/ -v
```

Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add tests/
git commit -m "feat: add tests for Suite and Case operations"
```

---

## Verification Checklist

After completing all tasks, verify:

- [ ] All tests pass
- [ ] No mypy errors (if type checking enabled)
- [ ] All API endpoints respond correctly
- [ ] Seed data creates demo suite with 3 cases
- [ ] Input validation works for all endpoints
- [ ] Error responses are properly formatted
- [ ] CORS headers present on all responses

## Next Steps

After completing this feature:

1. **Task 03: Run Execution** - Implement comparison run orchestration
2. Test the API endpoints with curl or Postman
3. Deploy to AWS and verify DynamoDB operations
